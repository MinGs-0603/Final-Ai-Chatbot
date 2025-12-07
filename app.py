import streamlit as st
from datetime import date, timedelta, datetime
import calendar

# --- 1. 환경 설정 및 초기화 ---

# 출석 기간 설정 (사용자 요청 기반)
START_DATE = date(2025, 12, 7) # 2025년 12월 7일
END_DATE = date(2026, 1, 14)   # 2026년 1월 14일
USER_NAME = "진민수" # 사용자 이름 고정
TODAY_TEST_DATE = date(2025, 12, 7) # 테스트를 위해 횟수 제한을 해제한 날짜

# Streamlit 페이지 설정
st.set_page_config(
    page_title=f"{USER_NAME} 출석 시스템 (달력 시각화)",
    page_icon="🗓️",
    layout="centered"
)

# 세션 상태 초기화 (출석 기록 저장)
# { '2025-12-07': '12:00:00', '2025-12-08': '09:30:00' } 형식으로 저장
if 'checked_dates_with_time' not in st.session_state:
    st.session_state.checked_dates_with_time = {}

# --- 2. 디자인 및 캘린더 CSS ---
st.markdown("""
    <style>
    /* 1. 기본 스타일 */
    .stApp {
        background: linear-gradient(135deg, #e6f7ff 0%, #ffffff 100%); /* 밝은 하늘색 배경 */
        font-family: 'Malgun Gothic', 'Apple Gothic', sans-serif;
    }
    
    /* 2. 제목 */
    h1 {
        color: #004a7c; /* 짙은 파랑 */
        text-align: center;
        padding-bottom: 10px;
        margin-bottom: 20px;
        font-weight: 900;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    /* 3. 출석 버튼 */
    .stButton>button {
        background-color: #4CAF50; /* 초록색 (성공 강조) */
        color: white;
        border-radius: 12px;
        border: none;
        padding: 10px 24px;
        font-size: 1.2rem;
        font-weight: bold;
        box-shadow: 0 4px 8px rgba(76, 175, 80, 0.4);
        transition: all 0.2s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 6px 12px rgba(76, 175, 80, 0.5);
    }
    
    /* 4. 메트릭 */
    div[data-testid="stMetric"] {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
        text-align: center;
        border-top: 5px solid #007bff;
    }
    div[data-testid="stMetricValue"] {
        color: #007bff !important;
        font-size: 2.2rem !important;
        font-weight: 900;
    }

    /* 5. 캘린더 스타일 */
    .calendar-container {
        padding: 20px;
        background-color: #ffffff;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
    }
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 5px;
        margin-top: 10px;
        text-align: center;
    }
    .day-header {
        font-weight: bold;
        color: #333;
        padding: 5px 0;
    }
    .day-box {
        padding: 8px 0;
        border-radius: 8px;
        font-weight: 600;
        cursor: default;
        transition: background-color 0.2s;
    }
    .day-box.weekend {
        color: #ff6347; /* 주말(토/일) */
    }
    .day-box.target {
        background-color: #f0f0f0;
    }
    .day-box.checked {
        background-color: #4CAF50; /* 출석 성공: 초록 */
        color: white;
        border: 2px solid #388e3c;
    }
    .day-box.today {
        background-color: #FFC107; /* 오늘: 노랑 */
        color: #333;
        border: 2px solid #ffa000;
        font-weight: 800;
    }
    .day-box.outside {
        color: #ccc; /* 기간 외 */
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 핵심 로직 함수 ---

def is_within_target_period(dt: date) -> bool:
    """날짜가 설정된 출석 기간 내에 있는지 확인합니다."""
    return START_DATE <= dt <= END_DATE

def get_total_target_days(start_dt: date, end_dt: date) -> set:
    """지정된 기간 내의 모든 요일(출석 목표일)을 계산합니다 (주말 포함)."""
    target_days = set()
    current = start_dt
    
    if start_dt > end_dt:
        return target_days

    if current < START_DATE:
        current = START_DATE
        
    while current <= end_dt:
        target_days.add(current)
        current += timedelta(days=1)
        
    return target_days

def calculate_streak(today: date, checked_dates: set) -> int:
    """연속 출석 일수를 계산합니다."""
    if not checked_dates:
        return 0

    streak = 0
    current_day = today
    
    # 오늘 출석했으면 오늘부터 카운트 시작
    if current_day in checked_dates:
        streak = 1
        current_day -= timedelta(days=1)

    # 어제부터 과거로 거슬러 올라가며 연속 기록 확인
    while current_day >= START_DATE:
        if current_day in checked_dates:
            streak += 1
        else:
            # 주말 포함 모든 날짜를 목표일로 하므로, 미출석 시 바로 연속 기록 중단
            break
        current_day -= timedelta(days=1)

    return streak

def check_attendance():
    """출석 버튼 클릭 시 실행되는 함수."""
    now = datetime.now()
    today = now.date()
    today_str = today.isoformat()
    time_str = now.strftime('%H:%M:%S')

    # 1. 기간 확인
    if not is_within_target_period(today):
        st.error("⚠️ 출석 기간이 아닙니다.")
        return
        
    # 2. 이미 출석했는지 확인 (오늘(TODAY_TEST_DATE)은 제한 해제)
    if today_str in st.session_state.checked_dates_with_time and today != TODAY_TEST_DATE:
        st.warning("✅ 이미 오늘 출석 체크를 완료했습니다. 내일 자정(24시) 이후에 다시 시도해 주세요.")
        return
        
    # 3. 출석 기록 및 성공 메시지
    st.session_state.checked_dates_with_time[today_str] = time_str
    
    if today == TODAY_TEST_DATE:
        st.success(f"🎉 **{USER_NAME}님, {today.strftime('%Y년 %m월 %d일')} {time_str} 출석 완료!**")
        st.info(f"🧪 테스트를 위해 오늘({TODAY_TEST_DATE.strftime('%Y년 %m월 %d일')})은 횟수 제한 없이 기록됩니다.")
    else:
        st.success(f"🎉 **{USER_NAME}님, {today.strftime('%Y년 %m월 %d일')} {time_str} 출석 완료!**")
        
    st.rerun() 

# --- 4. 달력 렌더링 함수 ---

def render_calendar(display_month: date):
    """지정된 월의 출석 상태를 달력 형태로 렌더링합니다."""
    
    st.subheader(f"📅 {display_month.year}년 {display_month.month}월 출석 현황")
    
    # 캘린더 컨테이너 시작
    st.markdown('<div class="calendar-container">', unsafe_allow_html=True)
    
    # 요일 헤더 (일요일부터 시작)
    day_names = ["일", "월", "화", "수", "목", "금", "토"]
    st.markdown(f"""
        <div class="calendar-grid">
            <div class="day-header" style="color: #ff6347;">{day_names[0]}</div>
            {''.join(f'<div class="day-header">{name}</div>' for name in day_names[1:-1])}
            <div class="day-header" style="color: #007bff;">{day_names[-1]}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 월별 달력 데이터 생성
    cal = calendar.Calendar(firstweekday=6) # 일요일을 주의 첫날로 설정
    month_data = cal.monthdatescalendar(display_month.year, display_month.month)
    
    today = date.today()
    checked_dates_set = {date.fromisoformat(d) for d in st.session_state.checked_dates_with_time.keys()}

    # 날짜 렌더링
    st.markdown('<div class="calendar-grid">', unsafe_allow_html=True)
    for week in month_data:
        for day in week:
            day_class = []
            
            # 1. 출석 성공
            if day in checked_dates_set:
                day_class.append("checked")
            # 2. 오늘
            elif day == today:
                day_class.append("today")
            
            # 3. 기간 내/외 구분
            if not is_within_target_period(day):
                day_class.append("outside")
            
            # 4. 주말 색상
            if day.weekday() == 5 or day.weekday() == 6: # 토요일(5) 또는 일요일(6)
                 day_class.append("weekend")
            
            # 5. 해당 월 외 날짜는 연하게 표시
            if day.month != display_month.month:
                day_class.append("outside")

            # 최종 클래스 문자열
            class_str = " ".join(day_class)
            
            # 오늘 날짜에 출석 시간 표시 (CSS 툴팁 등 복잡한 기능은 생략하고 간단히)
            if day == today and day.isoformat() in st.session_state.checked_dates_with_time:
                 day_text = f"{day.day}"
            else:
                 day_text = str(day.day)

            # 날짜 박스 렌더링
            st.markdown(f'<div class="day-box {class_str}">{day_text}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    

# --- 5. 메인 UI 렌더링 ---

st.title(f"✨ {USER_NAME} 출석 관리 대시보드")
st.info(f"**기간:** `{START_DATE.strftime('%Y년 %m월 %d일')} ~ {END_DATE.strftime('%Y년 %m월 %d일')}` **(주말 포함)**")

today = date.today()
today_str = today.isoformat()
is_today_checked = today_str in st.session_state.checked_dates_with_time

# 출석 버튼 비활성화 로직
disable_button = is_today_checked and today != TODAY_TEST_DATE

# 출석 버튼 및 상태 표시
with st.container():
    col_btn, col_status = st.columns([1, 1])
    
    with col_btn:
        st.button("✅ 오늘 출석하기", on_click=check_attendance, disabled=disable_button)

    with col_status:
        if is_today_checked:
            st.success(f"**✅ 출석 완료!** ({st.session_state.checked_dates_with_time[today_str]})")
        elif not is_within_target_period(today):
            st.info("🚫 **기간 외**")
        else:
            st.warning("🔔 **오늘 출석 미완료**")

st.markdown("---")

# --- 6. 통계 및 진행률 계산 ---

total_target_days_set = get_total_target_days(START_DATE, END_DATE)
total_target_count = len(total_target_days_set)

checked_dates_set = {date.fromisoformat(d) for d in st.session_state.checked_dates_with_time.keys()}
successful_checked_days = checked_dates_set.intersection(total_target_days_set)
checked_count = len(successful_checked_days)

# 연속 출석 기록 계산
current_streak = calculate_streak(today, checked_dates_set)


if total_target_count > 0:
    attendance_percentage = (checked_count / total_target_count) * 100
    
    st.header("📈 출석 현황 분석")
    
    col_prog, col_metrics_1, col_metrics_2 = st.columns([1, 1, 1])
    
    with col_prog:
        st.subheader("총 진행률")
        st.progress(attendance_percentage / 100)
    
    with col_metrics_1:
        st.metric(
            label="총 목표 달성률", 
            value=f"{attendance_percentage:.1f}%",
            delta=f"{checked_count}일 / {total_target_count}일"
        )
    with col_metrics_2:
        st.metric(
            label="🔥 연속 출석 일수", 
            value=f"{current_streak}일",
            delta="동기 부여!"
        )

st.markdown("---")

# --- 7. 달력 시각화 렌더링 ---

# 출석 기간이 12월과 1월에 걸쳐 있으므로 두 달을 모두 표시
render_calendar(date(2025, 12, 1))
render_calendar(date(2026, 1, 1))

st.markdown("---")

# --- 8. 상세 기록 (시간 포함) ---

st.header("📝 상세 출석 기록 (시간 포함)")
with st.expander(f"총 {checked_count}개의 기록 보기"):
    if st.session_state.checked_dates_with_time:
        sorted_records = sorted(st.session_state.checked_dates_with_time.items(), key=lambda item: item[0], reverse=True)
        
        for d_str, t_str in sorted_records:
            st.markdown(f"**🗓️ {d_str}** | ⏰ **{t_str}**")
    else:
        st.info("기록이 없습니다.")