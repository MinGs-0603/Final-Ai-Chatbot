import streamlit as st
from supabase import create_client
import requests
import re
import pandas as pd
import json

# -------------------------------------------------------------------------
# 1. 설정 및 초기화
# -------------------------------------------------------------------------

# Supabase 설정 (secrets 우선)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://qipphcdzlmqidhrjnjtt.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFpcHBoY2R6bG1xaWRocmpuanR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5NTIwMTIsImV4cCI6MjA4MjUyODAxMn0.AsuvjVGCLUJF_IPvQevYASaM6uRF2C6F-CjwC3eCNVk")

# Gemini API Key (secrets에서 읽기)
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "AIzaSyAQaiwm46yOITEttdr0ify7duXCW3TwGRo")


@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = init_supabase()

# -------------------------------------------------------------------------
# 2. 파싱 및 유틸리티 함수
# -------------------------------------------------------------------------

def extract_date_info(text):
    """질문에서 날짜(YYYY-MM-DD)와 월(MM) 정보를 추출"""
    info = {"date": None, "month": None, "year": "2025"}

    match_date = re.search(r"(\d{1,2})월\s*(\d{1,2})일", text)
    if match_date:
        m, d = match_date.groups()
        info["month"] = int(m)
        info["date"] = f"{info['year']}-{int(m):02d}-{int(d):02d}"
    else:
        match_month = re.search(r"(\d{1,2})월", text)
        if match_month:
            info["month"] = int(match_month.group(1))

    return info


def extract_version(text):
    if "0차" in text or "초기" in text or "계획" in text:
        return "0차"
    return "최종"


def extract_product_keyword(text):
    ignore_words = [
        "생산량", "알려줘", "비교해줘", "비교", "제품", "최종", "0차", "월", "일", "capa", "카파",
        "초과", "어떻게", "돼", "있어", "사례", "총", "fan", "motor", "flange", "팬", "모터", "플랜지"
    ]
    words = text.split()
    for w in words:
        clean_w = re.sub(r"[^a-zA-Z0-9가-힣]", "", w)
        if clean_w and clean_w.lower() not in ignore_words and not re.match(r"\d+(월|일)", clean_w):
            return clean_w
    return None


def normalize_line_name(line_val):
    """
    daily_capa의 '1','2','3' (int/str) -> '조립1','조립2','조립3'
    daily_total_production의 '조립1' -> '조립1' (유지)
    """
    s = str(line_val).strip()
    if s == '1':
        return '조립1'
    if s == '2':
        return '조립2'
    if s == '3':
        return '조립3'
    if '조립' in s:
        return s
    return s


def normalize_date(date_val):
    """
    날짜 문자열에서 시간 부분을 제거하고 YYYY-MM-DD 형식만 남김
    예: 2025-09-05T00:00:00 -> 2025-09-05
    """
    if not date_val:
        return ""
    s = str(date_val).strip()
    if len(s) >= 10:
        return s[:10]
    return s


# -------------------------------------------------------------------------
# 3. 데이터 조회 로직
# -------------------------------------------------------------------------

def fetch_db_data(user_input):
    info = extract_date_info(user_input)
    target_date = info["date"]
    target_month = info["month"]
    target_version = extract_version(user_input)
    product_key = extract_product_keyword(user_input)

    context_log = ""

    try:
        # =================================================================
        # 1. 과거 이슈 사례 검색 (MDL1 ~ CCL)
        # =================================================================
        if "사례" in user_input:
            issue_mapping = {
                "MDL1": {"keywords": ["먼저", "줄여", "순위", "교체"], "db_text": "생산순위 조정", "title": "MDL1: 미달(생산순위 조정/모델 교체)"},
                "MDL2": {"keywords": ["감사", "정지", "설비", "라인전체"], "db_text": "라인전체이슈", "title": "MDL2: 미달(라인전체이슈/설비)"},
                "MDL3": {"keywords": ["부품", "자재", "결품", "수급", "안되는"], "db_text": "자재결품", "title": "MDL3: 미달(부품수급/자재결품)"},
                "PRP": {"keywords": ["선행", "미리", "당겨", "땡겨"], "db_text": "선행 생산", "title": "PRP: 선행 생산(숙제 미리하기)"},
                "SMP": {"keywords": ["샘플", "긴급"], "db_text": "계획외 긴급 생산", "title": "SMP: 계획외 긴급 생산"},
                "CCL": {"keywords": ["취소"], "db_text": "계획 취소", "title": "CCL: 계획 취소/라인 가동중단"}
            }

            detected_code = None
            for code, meta in issue_mapping.items():
                if any(k in user_input for k in meta["keywords"]):
                    detected_code = code
                    break

            if detected_code:
                meta = issue_mapping[detected_code]
                query = supabase.table("production_issue_analysis_8_11").select("품목명, 날짜, 계획_v0, 실적_v2, 누적차이_Gap, 최종_이슈분류")

                if detected_code == "MDL2":
                    query = query.or_(f"최종_이슈분류.ilike.%라인전체이슈%,최종_이슈분류.ilike.%설비%")
                elif detected_code == "MDL3":
                    query = query.or_(f"최종_이슈분류.ilike.%부품수급%,최종_이슈분류.ilike.%자재결품%")
                else:
                    query = query.ilike("최종_이슈분류", f"%{meta['db_text']}%")

                response = query.limit(3).execute()

                if response.data:
                    context_log += f"[{detected_code} CASE FOUND]\n"
                    context_log += f"Title: {meta['title']}\n"
                    context_log += f"Data: {json.dumps(response.data, ensure_ascii=False)}"
                    return context_log
                else:
                    return "관련된 과거 유사 사례를 찾을 수 없습니다."

        # =================================================================
        # 2. 월간 생산량 브리핑
        # =================================================================
        found_months = re.findall(r"(\d{1,2})월", user_input)
        found_months = sorted(list(set([int(m) for m in found_months])))

        if len(found_months) >= 2 and product_key is None:
            target_ver = extract_version(user_input)
            res = supabase.table("monthly_production").select("월, 총_생산량").in_("월", found_months).eq("버전", target_ver).execute()

            if res.data:
                df = pd.DataFrame(res.data)
                df = df.sort_values(by='월')
                context_log += f"\n[{target_ver} 월간 총 생산량 브리핑]\n"
                prev_val = None
                prev_month = None
                for _, row in df.iterrows():
                    m = row['월']
                    val = row['총_생산량']
                    msg = f"{m}월: {val:,}"
                    if prev_val is not None:
                        diff = val - prev_val
                        if diff > 0:
                            msg += f" (전월({prev_month}월) 대비 {diff:,} 증가 🔺)"
                        elif diff < 0:
                            msg += f" (전월({prev_month}월) 대비 {abs(diff):,} 감소 🔻)"
                        else:
                            msg += " (변동 없음)"
                    context_log += f"- {msg}\n"
                    prev_val = val
                    prev_month = m
                return context_log
            else:
                return "요청하신 월의 데이터가 monthly_production 테이블에 없습니다."

        # =================================================================
        # 3. 단순 CAPA 조회 ("00월 CAPA 알려줘")
        # =================================================================
        if target_month and ("capa" in user_input.lower() or "카파" in user_input) and "비교" not in user_input and "초과" not in user_input and not target_date:
            res_capa = supabase.table("daily_capa").select("라인, capa").eq("월", target_month).eq("버전", target_version).execute()
            if res_capa.data:
                df = pd.DataFrame(res_capa.data)
                df['라인'] = df['라인'].apply(normalize_line_name)
                display_data = {}
                grouped = df.groupby('라인')['capa'].apply(list).to_dict()
                for line, capas in grouped.items():
                    unique_capas = sorted(list(set(capas)))
                    display_data[line] = unique_capas[0] if len(unique_capas) == 1 else unique_capas
                context_log += f"\n[{target_month}월 {target_version} 라인별 CAPA 정보 (컬럼값)]: {display_data}"
                return context_log
            else:
                context_log += f"\n[{target_month}월 {target_version} CAPA 데이터가 없습니다.]"
                return context_log

        # =================================================================
        # 4. CAPA 초과 / 비교 로직
        # =================================================================
        if ("비교" in user_input and "월" in user_input and product_key is None) or ("초과" in user_input and "월" in user_input):
            res_capa = supabase.table("daily_capa").select("*").eq("월", target_month).eq("버전", "최종").execute()
            res_prod = supabase.table("daily_total_production").select("*").eq("월", target_month).eq("버전", "최종").execute()

            if not res_capa.data or not res_prod.data:
                context_log += f"\n[알림] 데이터 조회 실패. Capa 데이터: {len(res_capa.data) if res_capa.data else 0}건, Prod 데이터: {len(res_prod.data) if res_prod.data else 0}건"
                return context_log

            capa_reference = {}
            for item in res_capa.data:
                line_key = normalize_line_name(item['라인'])
                capa_reference[line_key] = item['capa']

            over_list = []
            for row in res_prod.data:
                p_date = normalize_date(row['날짜'])
                p_line = normalize_line_name(row['라인'])
                p_qty = row['총_생산량']

                limit = capa_reference.get(p_line, 0)

                if limit > 0 and p_qty > limit:
                    over_list.append(f"| {p_date} | {p_line} | {limit} | {p_qty} |")

            if "초과" in user_input:
                if over_list:
                    over_list.sort()
                    context_log += f"\n[CAPA 초과 리스트 (형식: 날짜|라인|CAPA|총 생산량)]:\n"
                    for item in over_list:
                        context_log += f"{item}\n"
                else:
                    context_log += f"\n[알림] {target_month}월 실적 데이터를 검토했으나, 설정된 CAPA를 초과한 날이 없습니다."
            else:
                context_log += f"\n[알림] {target_month}월 데이터 비교 완료. (총 실적 데이터 {len(res_prod.data)}건 검토됨)"

            return context_log

        # =================================================================
        # 5. 기타 조회
        # =================================================================
        gubun_keywords = ["fan", "motor", "flange", "팬", "모터", "플랜지"]
        if target_month and any(k in user_input.lower() for k in gubun_keywords):
            if "fan" in user_input.lower() or "팬" in user_input:
                target_gubun = "Fan"
            elif "motor" in user_input.lower() or "모터" in user_input:
                target_gubun = "Motor"
            else:
                target_gubun = "Flange"

            query = supabase.table("production_data").select("생산량") \
                .eq("월", target_month) \
                .eq("버전", "최종") \
                .ilike("구분", f"%{target_gubun}%")
            res = query.execute()
            if res.data:
                total_qty = sum([item['생산량'] for item in res.data])
                context_log += f"\n[{target_month}월 {target_gubun} (최종) 총 생산량]: {total_qty:,} (데이터 {len(res.data)}건 합계)"
            else:
                context_log += f"\n[{target_month}월 {target_gubun} 데이터가 없습니다.]"
            return context_log

        if target_date and product_key:
            query_prod = supabase.table("production_data").select("*")
            query_prod = query_prod.ilike("품명", f"%{product_key}%")

            if "비교" in user_input:
                res_v0 = supabase.table("production_data").select("*").eq("납기일", target_date).eq("버전", "0차").ilike("품명", f"%{product_key}%").execute()
                res_final = supabase.table("production_data").select("*").eq("생산일", target_date).eq("버전", "최종").ilike("품명", f"%{product_key}%").execute()
                v0_qty = sum([x['생산량'] for x in res_v0.data]) if res_v0.data else 0
                final_qty = sum([x['생산량'] for x in res_final.data]) if res_final.data else 0
                context_log += f"\n[비교 결과 ({target_date} {product_key})]\n"
                context_log += f"- 0차(납기일 기준): {v0_qty}\n"
                context_log += f"- 최종(생산일 기준): {final_qty}\n"
            else:
                ver_col = "납기일" if target_version == "0차" else "생산일"
                query_prod = query_prod.eq("버전", target_version).eq(ver_col, target_date)
                res_prod = query_prod.execute()
                if res_prod.data:
                    context_log += f"\n[제품 데이터 ({target_version})]: {res_prod.data}"
                    total_p = sum([x.get('생산량', 0) for x in res_prod.data])
                    context_log += f"\n[총 생산량]: {total_p}"
                else:
                    context_log += f"\n[알림] '{target_date}'에 '{product_key}' 제품의 {target_version} 데이터가 없습니다."
            return context_log

        if target_date and "생산량" in user_input:
            res = supabase.table("daily_total_production").select("총_생산량").eq("날짜", target_date).eq("버전", target_version).execute()
            if res.data:
                total_qty = sum([item['총_생산량'] for item in res.data])
                context_log += f"\n[{target_date} {target_version} 총 생산량]: {total_qty:,} (daily_total 합계)"
            else:
                ver_col = "납기일" if target_version == "0차" else "생산일"
                res_fallback = supabase.table("production_data").select("생산량").eq(ver_col, target_date).eq("버전", target_version).execute()
                if res_fallback.data:
                    total = sum([x['생산량'] for x in res_fallback.data])
                    context_log += f"\n[{target_date} {target_version} 총 생산량 (Item 집계)]: {total:,}"
                else:
                    context_log += f"\n[{target_date} 데이터가 없습니다.]"
            return context_log

        if target_date and ("capa" in user_input.lower() or "카파" in user_input):
            res = supabase.table("daily_capa").select("*").eq("날짜", target_date).eq("버전", target_version).execute()
            if res.data:
                context_log += f"\n[{target_date} {target_version} CAPA 정보]: {res.data}"
            else:
                context_log += f"\n[{target_date} CAPA 데이터가 없습니다.]"
            return context_log

    except Exception as e:
        return f"데이터 조회 중 오류 발생: {str(e)}"

    if not context_log:
        return "요청하신 조건에 맞는 데이터를 찾을 수 없습니다."

    return context_log


# -------------------------------------------------------------------------
# 4. LLM 응답 생성 (Gemini 2.0 Flash Experimental 적용)
# -------------------------------------------------------------------------

def query_gemini_ai(user_input, context):
    system_prompt = f"""
당신은 숙련된 생산계획 담당자입니다. 제공된 데이터(Context)를 기반으로 사용자의 질문에 답하세요.

[중요: CAPA 초과 답변 규칙]
Context에 '[CAPA 초과 리스트]'가 포함되어 있다면, 반드시 아래 형식의 마크다운 표(Table)로 출력하세요.
(Context에 있는 데이터를 그대로 사용하세요.)

| 날짜 | 라인 | CAPA | 총 생산량 |
|---|---|---|---|
| ... | ... | ... | ... |

[중요: 이슈 코드 답변 규칙]
Context에 [CODE CASE FOUND]가 있다면:
1. 답변 최상단에 코드명과 제목을 # Heading 1로 적으세요.
2. 데이터(Data)를 바탕으로 표를 작성하세요: [날짜 | 품목명 | 계획(V0) | 실적(V2) | 차이(Gap)]

[일반 답변 규칙]
1. 숫자는 제공된 그대로 전달하세요.
2. 데이터가 없으면 없다고 하세요.
3. CAPA 초과 질문 시, 초과 리스트가 있으면 표를 보여주고, 없으면 없다고 명확히 말하세요.

[Context Data]:
{context}

[User Question]:
{user_input}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    data = {"contents": [{"parts": [{"text": system_prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            try:
                return result['candidates'][0]['content']['parts'][0]['text']
            except Exception:
                return "응답 파싱 실패"
        else:
            return f"API 오류: {response.status_code}"
    except Exception as e:
        return f"통신 오류: {e}"


# -------------------------------------------------------------------------
# 5. UI (탭에서 호출)
# -------------------------------------------------------------------------

def render_legacy_chatbot():
    st.subheader("🏭 생산계획 보조 챗봇")
    st.caption("예: 9월 5일 최종 생산량 알려줘 / 10월 CAPA 초과한 날 있어? / 9월 10월 최종 총 생산량 브리핑")

    if "legacy_messages" not in st.session_state:
        st.session_state.legacy_messages = []

    for message in st.session_state.legacy_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(
        "질문을 입력하세요 (예: 9월 5일 최종 생산량 알려줘, 10월 CAPA 초과한 날 있어?)",
        key="legacy_input"
    ):
        st.session_state.legacy_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("데이터 분석 중..."):
                db_result = fetch_db_data(prompt)
                if "찾을 수 없습니다" in db_result or "오류" in db_result:
                    final_response = db_result
                else:
                    final_response = query_gemini_ai(prompt, db_result)
                st.markdown(final_response)

        st.session_state.legacy_messages.append({"role": "assistant", "content": final_response})
