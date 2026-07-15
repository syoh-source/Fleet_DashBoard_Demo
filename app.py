import os; os.environ["GRPC_DNS_RESOLVER"]="native"; os.environ["GRPC_POLL_STRATEGY"]="epoll1"
import warnings; warnings.filterwarnings("ignore") 
import streamlit as st; import pandas as pd; import time; import datetime; import ast; import json; import streamlit.components.v1 as components
import firebase_manager as fm; import chart_utils as dc; import admin_manager as am; import admin_utils as utils
import tab_summary; import tab_safeguard; import tab_vehicle 
import dummy_data

class DummyAdm:
    def get_cached_raw_data(self): return [], [], []
try: import admin_data as adm
except: adm = DummyAdm()

st.set_page_config(layout="wide", page_title="운영 대시보드", page_icon="🚖")
@st.cache_resource
def get_global_sync_state(): return {'last_sync_time': 0.0}
global_state = get_global_sync_state()

st.markdown("<style>.stApp { background-color: #f8fafc; } .stTabs [data-baseweb=\"tab-list\"] { gap: 8px; background-color: #ffffff; padding: 8px 12px; border-radius: 18px; box-shadow: 0 4px 10px rgba(0,0,0,0.03); } .stTabs [data-baseweb=\"tab\"] { background-color: transparent; border-radius: 12px; padding: 10px 20px; font-size: 16px; font-weight: 600; border: none; color: #64748b; } .stTabs [aria-selected=\"true\"] { background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; color: white !important; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.4); } hr { border-color: #e2e8f0 !important; } [data-testid=\"stVerticalBlockBorderWrapper\"] { border-radius: 20px !important; box-shadow: 0 4px 20px rgba(0,0,0,0.03) !important; border: 1px solid #f1f5f9 !important; background-color: #ffffff !important; }</style>", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.update({'logged_in': False, 'user_role': None, 'user_name': None, 'user_position': None, 'settings_unlocked': False, 'is_mobile': False, 'shift': '주간 (08:00~17:30)', 'region': '상암', 'view_region': '전체', 'is_demo': False})

if not st.session_state.logged_in:
    st.title("🚖 운영 대시보드"); st.markdown("---"); c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        t_login, t_signup, t_change = st.tabs(["🔑 로그인", "📝 회원 가입", "🔄 정보 변경 신청"])
        with t_login:
            st.markdown("<div style='margin-bottom: 5px; font-size: 14px; font-weight: 600; color: #475569;'>🖥️ 접속 환경 선택</div>", unsafe_allow_html=True)
            device_mode = st.radio("접속 기기", ["💻 PC / 태블릿", "📱 모바일 (스마트폰)"], horizontal=True, label_visibility="collapsed")
            u_id = st.text_input("사내 통합 아이디", key="main_login_id"); u_pw = st.text_input("비밀번호", type="password", key="main_login_pw")
            KST = datetime.timezone(datetime.timedelta(hours=9))
            kst_now = datetime.datetime.now(KST)
            expiry_date = datetime.date(2026, 7, 20) 
            if st.button("로그인 🚀", use_container_width=True):
                if u_id == "portfolio" and u_pw == "trial":
                    if kst_now.date() > expiry_date: st.error("⏳ 기간 만료", icon="🚫")
                    else:
                        st.session_state.update({'logged_in': True, 'user_id': u_id, 'user_role': 'admin', 'user_name': '임시접속(Guest)', 'user_position': 'Data Manager', 'is_mobile': "모바일" in device_mode, 'shift': '주간 (08:00~17:30)', 'region': '전체', 'is_demo': True})
                        st.rerun()
                elif u_id and u_pw:
                    with st.spinner("DB 통신 중..."): s, u_data, msg = fm.authenticate_user(u_id, u_pw)
                    if s:
                        st.session_state.update({'logged_in': True, 'user_id': u_id, 'user_role': u_data.get('role', 'user'), 'user_name': u_data.get('name'), 'user_position': u_data.get('position', 'Safe Guard'), 'is_mobile': "모바일" in device_mode, 'shift': u_data.get('shift', '주간 (08:00~17:30)'), 'region': u_data.get('region', '상암'), 'is_demo': False})
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("입력해주세요.")
    st.stop()

st.title("🚖 운영 대시보드")
st.sidebar.success(f"👤 **{st.session_state.user_name}**님 ({st.session_state.user_position})\n\n🕒 {st.session_state.shift}\n\n📍 {st.session_state.region}")

@st.cache_resource(ttl=60)
def get_dashboard_data():
    if st.session_state.get('is_demo', False): return dummy_data.get_demo_data()
    _, m = fm.get_master_data()
    return {'m_cars': m.get('cars', []), 'm_drivers': m.get('drivers', []), 'u_df': pd.DataFrame(fm.get_all_users()), 'df': pd.DataFrame(fm.get_ride_logs()), 'df_drive': pd.DataFrame(fm.get_driving_logs()), 'sched_df': pd.DataFrame(fm.get_schedules() if fm.get_schedules() else [])}

with st.spinner("🚀 데이터 로딩 중..."):
    d_data = get_dashboard_data(); m_cars, m_drivers = d_data['m_cars'], d_data['m_drivers']
    u_df = d_data['u_df'].copy(); df = d_data['df'].copy(); df_drive = d_data['df_drive'].copy(); sched_df = d_data['sched_df'].copy()

if not u_df.empty: u_df['name'] = u_df['name'].astype(str).str.strip()
user_dict = u_df.set_index('name')[['region', 'shift']].to_dict('index') if not u_df.empty else {}

if not df.empty:
    df['dt_obj'] = pd.to_datetime(df.get('ride_start_time', df.get('timestamp')), unit='ms', utc=True).dt.tz_convert('Asia/Seoul')
    df['shift_date'] = df['dt_obj'].apply(dc.get_shift_date)
    df['timestamp_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['driverName'] = df.get('driverName', '').astype(str).str.strip()
    df['carNumber'] = df.get('carNumber', '').astype(str).str.strip()
    df['status'] = df.get('status', '')
    df['region'] = df['driverName'].map(lambda x: user_dict.get(x, {}).get('region', '미정'))
    df['shift'] = df['driverName'].map(lambda x: user_dict.get(x, {}).get('shift', '주간 (08:00~17:30)'))
else: df = pd.DataFrame(columns=['timestamp_str', 'date_str', 'shift_date', 'dt_obj', 'carNumber', 'driverName', 'passengers', 'callCount', 'remark', 'status', 'region', 'shift'])

if not df.empty:
    df['duration_min'] = ((pd.to_datetime(df['ride_end_time'], unit='ms', errors='coerce') - pd.to_datetime(df['ride_start_time'], unit='ms', errors='coerce')).dt.total_seconds() / 60).fillna(0)
    df['revenue'] = df.apply(dc.calc_revenue, axis=1)
    df['이슈건수'] = df.apply(dc.get_global_issue_count, axis=1)
    df['chart_category'] = df.apply(dc.classify_data, axis=1)
    df['hour'] = df['dt_obj'].dt.hour
    df['time_bracket'] = df['hour'].apply(dc.get_time_bracket)
    df['is_manual'] = df['chart_category'].apply(lambda x: '📦 일괄 입력' if '일괄' in x else '🚕 정상 운행')
else:
    df['duration_min'] = 0; df['revenue'] = 0; df['이슈건수'] = 0; df['chart_category'] = '기록없음'; df['hour'] = 0; df['time_bracket'] = '기타'; df['is_manual'] = '🚕 정상 운행'

required_cols = {'출발_km':0, '종료_km':0, '총주행거리(km)':0, '특이사항':'-', '출발_배터리_차량':0, '종료_배터리_차량':0, '유형':'알수없음'}
for col, val in required_cols.items():
    if col not in df_drive.columns: df_drive[col] = val

f_drive = df_drive.copy()
clean_df = df.copy()

el = time.time() - global_state['last_sync_time']
with st.sidebar:
    if st.button("🔄 수동 동기화", use_container_width=True): st.rerun()

t_titles = ["📊 통합 Summary", "🧑‍✈️ Safe Guard 별", "🚗 차량 별"]
if st.session_state.user_role in ['admin', 'DM']: t_titles.append("⚙️ 시스템 관리")
tbs = st.tabs(t_titles)

with tbs[0]: tab_summary.draw_summary_tab(clean_df, f_drive)
with tbs[1]: tab_safeguard.draw_safeguard_tab(clean_df, f_drive, sched_df)
with tbs[2]: tab_vehicle.draw_car_tab(clean_df, f_drive) 
if st.session_state.user_role in ['admin', 'DM']:
    with tbs[3]: am.draw_admin_tab(clean_df, f_drive, u_df, sched_df, m_cars, m_drivers, datetime.datetime.now())
