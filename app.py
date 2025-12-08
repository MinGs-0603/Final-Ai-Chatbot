import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import altair as alt
import calendar

# --- 1. 환경 설정 및 초기화 ---

# 5명의 팀원 이름 설정
USER_NAMES = ["김도원", "진민수", "김나리", "김기범", "이소현"]

# 출석 기간 설정 (오늘 날짜로 자동 업데이트)
START_DATE = date.today()       # 오늘 날짜로 설정
END_DATE = START_DATE + timedelta(days=40)  # 시작일로부터 40일 후로 종료일 설정

# Streamlit 페이지 설정
st.set_page_config(
    page_title=f"팀 출석 관리 대시보드 ({len(USER_NAMES)}명)",
    page_icon="🏆",
    layout="wide" # 레이아웃 확장 (Wide Layout)
)

# 세션 상태 초기화 (출석 기록 저장)
if 'checked_dates_by_user' not in st.session_state:
    # 딕셔너리 구조: {사용자 이름: {날짜(ISO): 시간(HH:MM:SS)}}
    st.session_state.checked_dates_by_user = {name: {} for name in USER_NAMES}

# --- 2. 디자인 및 CSS (고급 테마 적용) ---
st.markdown("""
    <style>
    /* 1. 기본 스타일 */
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
        border-radius: 8px;
        border: none;
        padding: 10px 15px;
        font-size: 1.1rem;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(44, 160, 44, 0.4);
        transition: all 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #1f8a1f;
        box-shadow: 0 6px 12px rgba(44, 160, 44, 0.5);
    }
    .stButton>button:disabled {
        background-color: #a0a0a0 !important;
        box-shadow: none;
    }
    
    /* 5. 메트릭 (카드 디자인) */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        text-align: left;
        border-left: 5px solid #1f77b4;
    }
    div[data-testid="stMetricValue"] {
        color: #1f77b4 !important;
        font-size: 2.5rem !important;
        font-weight: 900;
    }
    
    /* 6. 캘린더 스타일 */
    .day-box.checked {
        background-color: #2ca02c; /* 출석 성공: 초록 */
        color: white;
        border: 2px solid #1f771f;
    }
    .day-box.today {
        background-color: #ff7f0e; /* 오늘: 주황 */
        color: white;
        border: 2px solid #d46a00;
        font-weight: 800;
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

    # 1. 기간 확인
    if not (START_DATE <= today <= END_DATE):
        st.error(f"{user_name}님, ⚠️ 출석 기간이 아닙니다.")
        return
        
    # 2. 이미 오늘 출석했는지 확인 (24시 리셋)
    if today_str in st.session_state.checked_dates_by_user[user_name]:
        st.warning(f"✅ {user_name}님, 이미 오늘 출석 체크를 완료했습니다. 내일 자정(24시) 이후에 다시 시도해 주세요.")
        return
        
    # 3. 출석 기록 및 성공 메시지
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

# --- 4. 캘린더 렌더링 함수 (생략, 필요시 추가) ---
# (공간 효율을 위해 달력은 현재 UI에서 제외하고, 추후 필요하면 추가하는 것을 권장)

# --- 5. 메인 UI 렌더링 ---

st.title("🏆 팀 프로젝트 출석 관리 대시보드")
st.caption(f"**기간:** `{START_DATE.strftime('%Y년 %m월 %d일')} ~ {END_DATE.strftime('%Y년 %m월 %d일')}` | **총 목표 출석일:** `{len(get_total_target_days(START_DATE, END_DATE))}일`")

st.markdown("---")

# 데이터프레임 계산
stats_df = calculate_all_stats(USER_NAMES)
total_target_days = stats_df['total_target_count'].iloc[0]
avg_percentage = stats_df['percentage'].mean()

# 5-1. 상단 통계 요약 (KPI)
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
        label="총 목표 출석일",
        value=f"{total_target_days}일",
        delta=f"종료일: {END_DATE.strftime('%Y-%m-%d')}"
    )

with col_kpi_3:
    st.metric(
        label="현재 출석률 최고 팀원",
        value=stats_df.loc[stats_df['percentage'].idxmax(), 'name'],
        delta=f"{stats_df['percentage'].max():.1f}%"
    )

st.markdown("---")

# 5-2. 팀원별 출석 버튼 및 상태
st.header("✅ 개인별 출석 체크 및 상태")
cols_check = st.columns(len(USER_NAMES))
today = date.today()
today_str = today.isoformat()

for i, name in enumerate(USER_NAMES):
    user_records = st.session_state.checked_dates_by_user.get(name, {})
    is_today_checked = today_str in user_records

    with cols_check[i]:
        st.subheader(name)
        
        # 출석 버튼
        st.button(
            "출석 완료" if is_today_checked else "오늘 출석하기", 
            key=f"btn_{name}", 
            on_click=check_attendance, 
            args=(name,), 
            disabled=is_today_checked or not (START_DATE <= today <= END_DATE)
        )
        
        # 상태 표시
        if is_today_checked:
            time_str = user_records[today_str]
            st.success(f"**완료!** ({time_str})")
        else:
            st.error("미완료")

st.markdown("---")

# 5-3. 그래프 섹션 (시각적 개선)
st.header("📈 팀원별 출석률 현황")
col_chart, col_progress = st.columns([1, 1])

# A. 좌측: 도넛 차트 (전체 팀 평균 기여도)
with col_chart:
    st.subheader("팀 전체 출석 기여도 (도넛 차트)")
    
    # 도넛 차트 데이터 준비: 이름, 출석 일수
    donut_df = stats_df[['name', 'checked_count']].copy()
    donut_df['Unchecked'] = donut_df['total_target_count'] - donut_df['checked_count']
    
    # 누적 막대 차트 생성
    chart = alt.Chart(donut_df).mark_bar().encode(
        y=alt.Y('name', title="팀원 이름", sort='-x'),
        x=alt.X('percentage', title="출석률 (%)"),
        color=alt.Color('percentage', scale=alt.Scale(range='ramp'), legend=None),
        tooltip=['name', 'checked_count', 'total_target_count', alt.Tooltip('percentage', format='.1f')]
    ).properties(
        height=300
    ).interactive() # 줌/패닝 가능
    
    # 도넛 차트로 만들려면 데이터 준비를 달리 해야 하지만,
    # Altair의 Bar Chart가 현재 데이터를 가장 명확하게 보여줍니다 (Horizontal Bar Chart).
    st.altair_chart(chart, use_container_width=True)


# B. 우측: 개인별 진척 막대 (UX 개선)
with col_progress:
    st.subheader("개인별 목표 달성 진척도")
    for index, row in stats_df.sort_values(by='percentage', ascending=False).iterrows():
        st.markdown(f"**{row['name']}** ({row['checked_count']}/{row['total_target_count']}일, **{row['percentage']:.1f}%**)")
        st.progress(row['percentage'] / 100)

st.markdown("---")

# 5-4. 상세 기록 섹션
st.header("📝 상세 출석 기록 확인")

selected_user = st.selectbox("기록을 확인할 팀원을 선택하세요:", USER_NAMES, key="record_select")
user_stats = get_user_stats(selected_user, get_total_target_days(START_DATE, END_DATE))

with st.expander(f"➡️ {selected_user}님의 상세 기록 (총 {user_stats['checked_count']}일 출석)"):
    if user_stats['records']:
        sorted_records = sorted(user_stats['records'].items(), key=lambda item: item[0], reverse=True)
        
        for d_str, t_str in sorted_records:
            st.markdown(f"**🗓️ {d_str}** | ⏰ **{t_str}**")
    else:
        st.info("아직 기록이 없습니다.")