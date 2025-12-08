import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import altair as alt
import calendar

# --- 1. 환경 설정 및 초기화 (D-Day 및 기간 설정 반영) ---

# 5명의 팀원 이름 설정
USER_NAMES = ["김도원", "진민수", "김나리", "김기범", "이소현"]

# 최종 보고일 (출석 마감일) 설정: 1월 12일
FINAL_REPORT_MONTH = 1
FINAL_REPORT_DAY = 12

# 현재 날짜 기준, 가장 가까운 1월 12일 연도 계산 (오늘이 1월 12일이 지났다면 다음 해로 설정)
today = date.today()
report_year = today.year
if today.month > FINAL_REPORT_MONTH or (today.month == FINAL_REPORT_MONTH and today.day > FINAL_REPORT_DAY):
    report_year += 1

FINAL_REPORT_DATE = date(report_year, FINAL_REPORT_MONTH, FINAL_REPORT_DAY)
START_DATE = today # 출석 시작일은 오늘 날짜부터
END_DATE = FINAL_REPORT_DATE

# D-Day 계산
time_diff = END_DATE - today
D_DAY_STR = f"D-{time_diff.days}" if time_diff.days >= 0 else "종료"


# Streamlit 페이지 설정
st.set_page_config(
    page_title=f"팀 출석 관리 대시보드 ({len(USER_NAMES)}명) | {D_DAY_STR}",
    page_icon="🏆",
    layout="wide"
)

# 세션 상태 초기화
if 'checked_dates_by_user' not in st.session_state:
    st.session_state.checked_dates_by_user = {name: {} for name in USER_NAMES}

# --- 2. 디자인 및 CSS (디자인 강화) ---
st.markdown("""
    <style>
    /* 1. 기본 스타일 및 배경 */
    .stApp {
        background: #f0f2f6; /* 부드러운 회색 배경 */
        font-family: 'Malgun Gothic', 'Apple Gothic', sans-serif;
        color: #1a1a1a;
    }
    
    /* 2. 대시보드 제목 */
    h1 {
        color: #1f77b4; /* 전문적인 파란색 */
        text-align: center;
        font-weight: 800;
        margin-bottom: 0px;
        padding-bottom: 0px;
    }

    /* 3. 섹션 헤더 */
    h2, h3 {
        color: #333333;
        border-bottom: 2px solid #ddd;
        padding-bottom: 5px;
        margin-top: 30px;
    }

    /* 4. 출석 버튼 */
    .stButton>button {
        background-color: #2ca02c; /* 성공적인 초록색 */
        color: white;
        border-radius: 12px; /* 둥근 모서리 강화 */
        border: none;
        padding: 10px 15px;
        font-size: 1.1rem;
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(44, 160, 44, 0.3); /* 그림자 부각 */
        transition: all 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1f8a1f;
        box-shadow: 0 6px 15px rgba(44, 160, 44, 0.4);
    }
    .stButton>button:disabled {
        background-color: #a0a0a0 !important;
        box-shadow: none;
    }
    
    /* 5. 메트릭 (KPI 카드 디자인 강조) */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 15px; /* 더 둥글게 */
        padding: 20px 25px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1); /* 그림자 강조 */
        text-align: left;
        border-left: 6px solid #1f77b4; /* 강조선 두께 증가 */
    }
    div[data-testid="stMetricValue"] {
        color: #1f77b4 !important;
        font-size: 2.8rem !important; /* 글자 크기 증가 */
        font-weight: 900;
    }
    
    /* 6. 개인별 진척도 섹션 컨테이너 스타일링 (진척도 강조) */
    .progress-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        border: 1px solid #e0e0e0;
    }

    /* 7. Streamlit Progress Bar 색상 (Streamlit 내부 클래스에 의존) */
    .stProgress > div > div > div > div {
        background-color: #2ca02c; /* 초록색 진척도 */
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 데이터 및 통계 함수 (변경 없음) ---

@st.cache_data
def get_total_target_days(start_dt: date, end_dt: date) -> set:
    """지정된 기간 내의 모든 요일(출석 목표일)을 계산합니다 (주말 포함)."""
    target_days = set()
    current = start_dt
    if start_dt > end_dt:
        return target_days
    while current <= end_dt:
        target_days.add(current)
        current += timedelta(days=1)
    return target_days

def check_attendance(user_name: str):
    """특정 사용자의 출석 버튼 클릭 시 실행되는 함수."""
    now = datetime.now()
    today = now.date()
    today_str = today.isoformat()
    time_str = now.strftime('%H:%M:%S')

    if not (START_DATE <= today <= END_DATE):
        st.error(f"{user_name}님, ⚠️ 출석 기간이 아닙니다. (마감일: {END_DATE.strftime('%Y-%m-%d')})")
        return
        
    if today_str in st.session_state.checked_dates_by_user[user_name]:
        st.warning(f"✅ {user_name}님, 이미 오늘 출석 체크를 완료했습니다. 내일 자정(24시) 이후에 다시 시도해 주세요.")
        return
        
    st.session_state.checked_dates_by_user[user_name][today_str] = time_str
    st.toast(f"🎉 {user_name}님 출석 완료! ({time_str})", icon="✅")
    st.rerun() 

def get_user_stats(user_name: str, total_target_days_set: set) -> dict:
    """사용자별 출석 통계를 계산합니다."""
    user_records = st.session_state.checked_dates_by_user.get(user_name, {})
    checked_dates_set = {date.fromisoformat(d) for d in user_records.keys()}
    successful_checked_days = checked_dates_set.intersection(total_target_days_set)
    checked_count = len(successful_checked_days)
    total_target_count = len(total_target_days_set)
    attendance_percentage = (checked_count / total_target_count) * 100 if total_target_count > 0 else 0
    return {
        "name": user_name,
        "checked_count": checked_count,
        "total_target_count": total_target_count,
        "percentage": attendance_percentage,
        "records": user_records
    }

def calculate_all_stats(user_list: list) -> pd.DataFrame:
    """모든 팀원의 통계를 계산하여 데이터프레임으로 반환합니다."""
    total_target_days_set = get_total_target_days(START_DATE, END_DATE)
    stats_list = [
        get_user_stats(name, total_target_days_set) 
        for name in user_list
    ]
    df = pd.DataFrame(stats_list)
    return df

# --- 4. 메인 UI 렌더링 (D-Day 및 개인별 진척도 강조) ---

st.title("🏆 팀 프로젝트 출석 관리 대시보드")
# D-Day를 h2 태그로 크게 표시하고 빨간색으로 강조
st.markdown(f"<h2 style='color: #d62728; margin-top: -10px; font-size: 2.2rem;'>**최종보고회 {D_DAY_STR}**</h2>", unsafe_allow_html=True) 
st.caption(f"**출석 기간:** `{START_DATE.strftime('%Y년 %m월 %d일')} ~ {END_DATE.strftime('%Y년 %m월 %d일')}` | **총 목표 출석일:** `{len(get_total_target_days(START_DATE, END_DATE))}일`")

st.markdown("---")

# 데이터프레임 계산
stats_df = calculate_all_stats(USER_NAMES)
total_target_days = stats_df['total_target_count'].iloc[0] if not stats_df.empty else 0
avg_percentage = stats_df['percentage'].mean() if not stats_df.empty else 0

# 4-1. 상단 통계 요약 (KPI)
st.header("✨ 팀 핵심 성과 지표 (KPI)")
col_kpi_1, col_kpi_2, col_kpi_3 = st.columns(3)

with col_kpi_1:
    st.metric(
        label="팀 평균 출석률",
        value=f"{avg_percentage:.1f}%",
        delta="성공적인 팀워크!"
    )

with col_kpi_2:
    st.metric(
        label="출석 목표일",
        value=f"{total_target_days}일",
        delta=f"최종 보고회: {END_DATE.strftime('%Y-%m-%d')}"
    )

with col_kpi_3:
    if not stats_df.empty and total_target_days > 0:
        max_percent = stats_df['percentage'].max()
        best_performer = stats_df.loc[stats_df['percentage'].idxmax(), 'name']
        st.metric(
            label="현재 출석률 최고 팀원",
            value=best_performer,
            delta=f"{max_percent:.1f}%"
        )
    else:
        st.metric(label="현재 출석률 최고 팀원", value="데이터 없음", delta="집계 기간이 아닙니다.")

st.markdown("---")

# 4-2. 팀원별 출석 버튼 및 상태
st.header("✅ 개인별 출석 체크 및 상태")
cols_check = st.columns(len(USER_NAMES))
today = date.today()
today_str = today.isoformat()
is_period_active = (START_DATE <= today <= END_DATE)

for i, name in enumerate(USER_NAMES):
    user_records = st.session_state.checked_dates_by_user.get(name, {})
    is_today_checked = today_str in user_records

    with cols_check[i]:
        st.subheader(name)
        
        button_text = "출석 완료" if is_today_checked else "오늘 출석하기"
        
        st.button(
            button_text, 
            key=f"btn_{name}", 
            on_click=check_attendance, 
            args=(name,), 
            disabled=is_today_checked or not is_period_active
        )
        
        if not is_period_active:
             st.warning("기간 마감")
        elif is_today_checked:
            time_str = user_records[today_str]
            st.success(f"**완료!** ({time_str})")
        else:
            st.error("미완료")

st.markdown("---")

# 4-3. 그래프 섹션 (개인별 진척도만 표시, 풀 와이드)
st.header("📈 팀원별 출석 목표 달성 현황")

if not stats_df.empty:
    st.subheader("개인별 최종 보고회 목표 진척도")
    
    # 정렬하여 출력
    for index, row in stats_df.sort_values(by='percentage', ascending=False).iterrows():
        # HTML/CSS 클래스를 사용하여 카드 디자인 적용
        st.markdown(
            f"""
            <div class="progress-card">
                <p style="font-size: 1.2rem; font-weight: bold; margin-bottom: 5px; color: #1f77b4;">
                    {row['name']}
                    <span style="float: right; color: #2ca02c;">{row['percentage']:.1f}%</span>
                </p>
                <p style="font-size: 0.9rem; color: #666; margin-bottom: 5px;">
                    출석 일수: {row['checked_count']}/{row['total_target_count']}일
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        # Streamlit 기본 진척 막대 표시
        st.progress(row['percentage'] / 100)
else:
    st.info("출석 기간이 설정되지 않았거나 목표일 수가 0입니다.")


st.markdown("---")

# 4-4. 상세 기록 섹션
st.header("📝 상세 출석 기록 확인")

selected_user = st.selectbox("기록을 확인할 팀원을 선택하세요:", USER_NAMES, key="record_select")
user_stats = get_user_stats(selected_user, get_total_target_days(START_DATE, END_DATE))

with st.expander(f"➡️ **{selected_user}**님의 상세 기록 (총 **{user_stats['checked_count']}**일 출석)"):
    if user_stats['records']:
        sorted_records = sorted(user_stats['records'].items(), key=lambda item: item[0], reverse=True)
        
        for d_str, t_str in sorted_records:
            record_date = date.fromisoformat(d_str)
            
            is_valid_attendance = START_DATE <= record_date <= END_DATE
            icon = "✅" if is_valid_attendance else "⚠️"
            status_text = "" if is_valid_attendance else " (기간 외 기록)"

            st.markdown(f"{icon} **🗓️ {d_str}** | ⏰ **{t_str}**{status_text}")
    else:
        st.info("아직 기록이 없습니다.")