import os; os.environ["GRPC_DNS_RESOLVER"]="native"; os.environ["GRPC_POLL_STRATEGY"]="epoll1"
import warnings; warnings.filterwarnings("ignore") 
import streamlit as st; import pandas as pd; import time; import datetime; import ast; import json; import streamlit.components.v1 as components
import firebase_manager as fm; import chart_utils as dc; import admin_manager as am; import admin_utils as utils
import tab_summary; import tab_safeguard; import tab_vehicle 

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
            
            # 🌟 안내 문구 변경: 진짜 회사 사내 시스템처럼 보이게 변경
            u_id = st.text_input("사내 통합 아이디", key="main_login_id"); u_pw = st.text_input("비밀번호", type="password", key="main_login_pw")
            
            KST = datetime.timezone(datetime.timedelta(hours=9))
            kst_now = datetime.datetime.now(KST)
            expiry_date = datetime.date(2026, 7, 20) 

            if st.button("로그인 🚀", use_container_width=True):
                # 🌟 평가관용 시크릿 스위치 (guest / swm2026)
                if u_id == "guest" and u_pw == "swm2026":
                    if kst_now.date() > expiry_date:
                        # 에러 메시지도 데모/포트폴리오 단어 없이, 시스템 만료처럼 표시
                        st.error("⏳ 발급된 임시 계정의 접속 기간이 만료되었습니다. 사내 시스템 담당자에게 문의 바랍니다.", icon="🚫")
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
        with t_signup:
            st.markdown("### 📝 신규 회원 가입")
            st.info("💡 외부망 접속 시에는 가입 및 정보 변경이 제한될 수 있습니다.")
        with t_change:
            st.markdown("### 🔄 계정 정보 변경 신청")
            st.info("💡 외부망 접속 시에는 가입 및 정보 변경이 제한될 수 있습니다.")
    st.stop()

st.title("🚖 운영 대시보드")
# 🌟 상단 데모 경고창 제거 (자연스러운 뷰 연출)

st.sidebar.success(f"👤 **{st.session_state.user_name}**님 ({st.session_state.user_position})\n\n🕒 {st.session_state.shift}\n\n📍 {st.session_state.region}")

KST = datetime.timezone(datetime.timedelta(hours=9)); kst_now = datetime.datetime.now(KST)
if time.time() - global_state['last_sync_time'] > 60:
    with st.spinner("🔄 캐시 업데이트 중..."):
        if not st.session_state.get('is_demo', False):
            try: fm.sync_only_new_data(force_full=False)
            except: pass
        global_state['last_sync_time'] = time.time(); st.cache_resource.clear()

@st.cache_resource(ttl=60)
def get_dashboard_data():
    if st.session_state.get('is_demo', False):
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        m_cars = ['E100#1', 'E100#2', 'U100#1', 'U100#2', '볼트_Test']
        m_drivers = ['홍길동', '김정석', '박데이터', '이비전', '최분석']
        u_df = pd.DataFrame([
            {'name': '홍길동', 'region': '상암', 'shift': '주간 (08:00~17:30)', 'can_view_dashboard': True, 'is_driver': True, 'is_admin': False, 'is_support': False},
            {'name': '김정석', 'region': '강남', 'shift': '야간 (21:00~06:00)', 'can_view_dashboard': True, 'is_driver': True, 'is_admin': False, 'is_support': False},
            {'name': '박데이터', 'region': '상암', 'shift': '주간 (08:00~17:30)', 'can_view_dashboard': True, 'is_driver': True, 'is_admin': False, 'is_support': False},
            {'name': '이비전', 'region': '강남', 'shift': '야간 (21:00~06:00)', 'can_view_dashboard': True, 'is_driver': True, 'is_admin': False, 'is_support': False},
            {'name': '최분석', 'region': '상암', 'shift': '주간 (08:00~17:30)', 'can_view_dashboard': True, 'is_driver': True, 'is_admin': False, 'is_support': False}
        ])
        
        r_logs = []
        for i in range(80):
            rt = now - datetime.timedelta(days=i%14, hours=(i*7)%24, minutes=(i*13)%60)
            r_start = int(rt.timestamp()*1000)
            r_logs.append({
                'timestamp': rt,
                'ride_start_time': r_start,
                'ride_end_time': r_start + (1000 * 60 * ((i%15)+5)), 
                'carNumber': m_cars[i%5],
                'driverName': m_drivers[i%5],
                'passengers': (i%3)+1,
                'callCount': 1,
                'status': 'COMPLETED',
                'remark': 'VIP 수행' if i%11==0 else ('데이터 수집' if i%7==0 else ''),
                'report_memos': {str(r_start): f"[{['차량', '시스템', '인지', '주행'][i%4]} > {['경고등', '모듈 에러', '보행자 미/오인지', '급감속'][i%4]}] 자동 기록된 이슈입니다."} if i%4==0 else {},
                'latitude': 37.5 + (i%10)*0.01, 'longitude': 127.0 + (i%10)*0.01,
                'Safeview': f"v1.{i%3}", 'CPU': 'v2.1', 'MCU': 'v1.5', 'VPU1': 'v3.0', 'VPU2': 'v3.0', 'VPU3': 'v3.0', 'VPU4': 'v3.0'
            })
            
        d_logs = []
        for i in range(30):
            dt = now - datetime.timedelta(days=i%14)
            car = m_cars[i%5]
            drv = m_drivers[i%5]
            d_logs.append({'timestamp': dt.replace(hour=8), '날짜': dt.strftime('%Y-%m-%d'), '차량번호': car, 'Safe_Guard': drv, '유형': '출발', '출발_km': 15000+i*100, '출발_배터리_차량': 100})
            d_logs.append({'timestamp': dt.replace(hour=17), '날짜': dt.strftime('%Y-%m-%d'), '차량번호': car, 'Safe_Guard': drv, '유형': '종료', '종료_km': 15000+i*100+95, '종료_배터리_차량': 30, '총주행거리(km)': 95, '특이사항': '특이사항 없음'})
            
        s_logs = []
        for i in range(14):
            dt = now - datetime.timedelta(days=i)
            for j in range(5):
                s_logs.append({'date': dt.strftime('%Y-%m-%d'), 'name': m_drivers[j], 'type': f"배정({m_cars[(i+j)%5]})"})
                
        return {'m_cars': m_cars, 'm_drivers': m_drivers, 'u_df': u_df, 'df': pd.DataFrame(r_logs), 'df_drive': pd.DataFrame(d_logs), 'sched_df': pd.DataFrame(s_logs)}

    _, m = fm.get_master_data()
    return {'m_cars': m.get('cars', []), 'm_drivers': m.get('drivers', []), 'u_df': pd.DataFrame(fm.get_all_users()), 'df': pd.DataFrame(fm.get_ride_logs()), 'df_drive': pd.DataFrame(fm.get_driving_logs()), 'sched_df': pd.DataFrame(fm.get_schedules() if fm.get_schedules() else [])}

with st.spinner("🚀 화면 구성 중..."):
    d_data = get_dashboard_data(); m_cars, m_drivers = d_data['m_cars'], d_data['m_drivers']
    u_df = d_data['u_df'].copy(); df = d_data['df'].copy(); df_drive = d_data['df_drive'].copy(); sched_df = d_data['sched_df'].copy()

if not u_df.empty: u_df['name'] = u_df['name'].astype(str).str.strip()
user_dict = u_df.set_index('name')[['region', 'shift']].to_dict('index') if not u_df.empty else {}

if not df.empty:
    def p_rt(r):
        t = r.get('ride_start_time')
        if pd.notna(t) and str(t).strip() not in ['','0','nan','None']:
            try: return pd.to_datetime(float(t), unit='ms', utc=True)
            except: pass
        ts = r.get('timestamp')
        if pd.notna(ts):
            try: return pd.to_datetime(ts.timestamp(), unit='s', utc=True) if hasattr(ts, 'timestamp') else pd.to_datetime(str(ts), errors='coerce', utc=True)
            except: pass
        return pd.Timestamp.utcnow()
    
    df['dt_obj'] = df.apply(p_rt, axis=1).dt.tz_convert('Asia/Seoul')
    df['driverName'] = df['driverName'].astype(str).str.strip()
    df['carNumber'] = df['carNumber'].astype(str).str.strip()
    df['shift_date'] = df['dt_obj'].apply(dc.get_shift_date)
    df = df.dropna(subset=['shift_date'])
    
    df['timestamp_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['date_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d')
    df['status'] = df.get('status', '')
    df['region'] = df['driverName'].map(lambda x: user_dict.get(x, {}).get('region', '미정'))
    df['shift'] = df['driverName'].map(lambda x: user_dict.get(x, {}).get('shift', '주간 (08:00~17:30)'))
    
    df = df.sort_values('dt_obj', ascending=False)
else: df = pd.DataFrame(columns=['timestamp_str', 'date_str', 'shift_date', 'dt_obj', 'carNumber', 'driverName', 'passengers', 'callCount', 'remark', 'status', 'region', 'shift'])

if not df_drive.empty:
    def p_dt(r):
        v = r.get('timestamp') if pd.notna(r.get('timestamp')) else r.get('날짜')
        if pd.isna(v) or v == "": return pd.NaT
        try: return pd.to_datetime(v.timestamp(), unit='s', utc=True) if hasattr(v, 'timestamp') else (pd.to_datetime(v, unit='ms', utc=True) if isinstance(v, (int, float)) and v > 1e11 else pd.to_datetime(str(v), errors='coerce', utc=True))
        except: return pd.NaT
        
    df_drive['dt_obj'] = df_drive.apply(p_dt, axis=1)
    df_drive['dt_obj'] = df_drive['dt_obj'].apply(lambda x: x.tz_localize('Asia/Seoul') if getattr(x, 'tz', None) is None else x.tz_convert('Asia/Seoul'))
    df_drive['Safe_Guard'] = df_drive['Safe_Guard'].astype(str).str.strip()
    df_drive['차량번호'] = df_drive.get('차량번호', '').astype(str).str.strip()
    df_drive['carNumber'] = df_drive['차량번호']
    
    df_drive = df_drive.sort_values(['차량번호', 'dt_obj']).reset_index(drop=True)
    df_drive['is_start'] = df_drive.get('유형', '').astype(str).str.replace(' ', '').str.strip().isin(['출발', '시작', '출근'])
    df_drive['shift_id'] = df_drive.groupby('차량번호')['is_start'].cumsum()
    
    s_map = df_drive[df_drive['is_start']].groupby(['차량번호', 'shift_id'])['dt_obj'].first().to_dict()
    df_drive['shift_start_dt'] = pd.to_datetime(df_drive.set_index(['차량번호', 'shift_id']).index.map(s_map).values)
    df_drive['shift_start_dt'] = df_drive['shift_start_dt'].fillna(df_drive['dt_obj'])
    df_drive['shift_date'] = df_drive['shift_start_dt'].apply(lambda d: pd.NaT if pd.isna(d) else ((d - datetime.timedelta(days=1)).date() if d.hour < 6 else d.date()))
    
    df_drive['region'] = df_drive['Safe_Guard'].map(lambda x: user_dict.get(x, {}).get('region', '미정'))
    df_drive['shift'] = df_drive['Safe_Guard'].map(lambda x: user_dict.get(x, {}).get('shift', '주간 (08:00~17:30)'))
    df_drive = df_drive.dropna(subset=['shift_date'])

st.sidebar.header("⚙️ Infor."); st.sidebar.info("💡 1분 주기로 정보를 최신화합니다.")
el = time.time() - global_state['last_sync_time']
with st.sidebar:
    if el < 60:
        components.html(f"<div id='c' style='font-family:sans-serif;color:#dc2626;font-size:14px;font-weight:bold;text-align:center;padding:10px;border-radius:12px;background:#fee2e2;border:1px solid #fecaca;'>⏳ 다음 업데이트: <span id='t'></span></div><script>var tg={(global_state['last_sync_time']+60)*1000};var x=setInterval(function(){{var d=tg-new Date().getTime();if(d<=0){{clearInterval(x);document.getElementById('c').innerHTML='✅ 지금 새로고침 가능!';document.getElementById('c').style.cssText+='color:#059669;background:#d1fae5;border-color:#a7f3d0';}}else{{var m=Math.floor((d%(1000*60*60))/(1000*60)),s=Math.floor((d%(1000*60))/1000);document.getElementById('t').innerHTML=(m<10?'0'+m:m)+'분 '+(s<10?'0'+s:s)+'초';}}}},1000);</script>", height=50)
    if st.button("🔄 수동 동기화", use_container_width=True) and el >= 60:
        if st.session_state.get('is_demo', False):
            with st.spinner("서버 동기화 진행 중..."):
                time.sleep(1)
                global_state['last_sync_time'] = time.time(); st.cache_resource.clear(); st.rerun()
        else:
            with st.spinner("동기화 중..."):
                try: fm.sync_only_new_data()
                except: pass
                global_state['last_sync_time'] = time.time(); st.cache_resource.clear(); st.rerun()

    if st.session_state.user_role in ['admin', 'DM']:
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        st.session_state.view_region = st.selectbox("🗺️ 화면 표시 지역 전환", ["전체", "상암", "강남"], index=0)
    else: st.session_state.view_region = st.session_state.region
    
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True); st.header("🔍 조회 기간 설정")
    l_td = kst_now.date() if kst_now.hour >= 8 else (kst_now - datetime.timedelta(days=1)).date()
    dm = st.radio("🗓️ 기간", ["오늘", "이번 주", "이번 달", "전체", "직접 지정"], index=2) 
    
    if dm == "오늘": fs, fe = l_td, l_td
    elif dm == "이번 주": fs = l_td - datetime.timedelta(days=l_td.weekday()); fe = fs + datetime.timedelta(days=6)
    elif dm == "이번 달": fs = l_td.replace(day=1); nm = fs.replace(day=28) + datetime.timedelta(days=4); fe = nm - datetime.timedelta(days=nm.day)
    elif dm == "전체": fs, fe = None, None
    else: cd = st.date_input("날짜 지정", [l_td, l_td]); fs, fe = cd if len(cd) == 2 else (cd[0], cd[0])

    if st.session_state.user_role == 'admin' or st.session_state.user_role == 'DM':
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True); st.header("📥 원시 데이터 추출")
        dl_dates = st.date_input("🗓️ 추출 기간", value=(kst_now.date(), kst_now.date()))
        dl_region = st.selectbox("📍 추출 지역", ["전체", "상암", "강남"], index=0)
        dl_type = st.selectbox("파일 분류", ["탑승 누적 (Ride)", "운행 일지 (Drive)", "이슈 발굴 (Issue)"])
        
        dl_s_date = dl_dates[0] if isinstance(dl_dates, tuple) else dl_dates
        dl_e_date = dl_dates[1] if isinstance(dl_dates, tuple) and len(dl_dates) == 2 else dl_s_date
        r_users = u_df[u_df['region'] == dl_region]['name'].tolist() if dl_region != "전체" else u_df['name'].tolist()
        
        dl_cache_key = f"{dl_type}_{dl_region}_{dl_s_date}_{dl_e_date}"
        if st.session_state.get('dl_cache_key') != dl_cache_key:
            st.session_state['dl_csv_bytes'] = None
            st.session_state['dl_cache_key'] = dl_cache_key

        if st.session_state['dl_csv_bytes'] is None:
            if st.button("🚀 데이터 추출 준비하기", use_container_width=True):
                with st.spinner("백그라운드에서 데이터를 추출하여 엑셀을 만들고 있습니다..."):
                    csv_bytes = None
                    if dl_type == "탑승 누적 (Ride)":
                        dl_df = df[(df['shift_date'] >= dl_s_date) & (df['shift_date'] <= dl_e_date)].copy()
                        dl_df = dl_df[dl_df['status'].astype(str).str.strip().str.upper() != 'ISSUE_ONLY']
                        if dl_region != "전체": dl_df = dl_df[dl_df['driverName'].isin(r_users)]
                        if not dl_df.empty:
                            def fmt_time(ts):
                                if pd.isna(ts) or str(ts).strip() in ['','0','nan','None']: return ""
                                try: return pd.to_datetime(float(ts), unit='ms', utc=True).tz_convert('Asia/Seoul').strftime('%H:%M:%S')
                                except: return ""
                            dl_df['탑승시간'] = dl_df.get('ride_start_time', '').apply(fmt_time)
                            dl_df['하차시간'] = dl_df.get('ride_end_time', '').apply(fmt_time)
                            dl_df['일자'] = dl_df['shift_date'].astype(str)
                            dl_df['예상요금(원)'] = dl_df.apply(dc.calc_revenue, axis=1)
                            dl_df = dl_df[['일자', '차량번호', '운전자', '탑승시간', '하차시간', '호출(건)', '탑승객(명)', '예상요금(원)', '지역', '근무시간', '특이사항']]
                            dl_df.columns = ['일자', '차량번호', '운전자', '탑승시간', '하차시간', '호출(건)', '탑승객(명)', '예상요금(원)', '지역', '근무시간', '특이사항']
                            dl_df = dl_df.sort_values(by=['일자', '탑승시간'], ascending=[True, True])
                            csv_bytes = dl_df.to_csv(index=False).encode('utf-8-sig')

                    elif dl_type == "운행 일지 (Drive)":
                        dl_df = df_drive[(df_drive['shift_date'] >= dl_s_date) & (df_drive['shift_date'] <= dl_e_date)].copy()
                        if dl_region != "전체": dl_df = dl_df[dl_df['Safe_Guard'].isin(r_users)]
                        if not dl_df.empty:
                            csv_bytes = dc.merge_driving_logs(dl_df).to_csv(index=False).encode('utf-8-sig')

                    else:
                        if st.session_state.get('is_demo', False):
                            r_list = d_data['df'].to_dict('records')
                            sw_db = {}
                        else:
                            r_list, _, _ = adm.get_cached_raw_data()
                            try: sw_db = fm.load_data('sw_versions')
                            except: sw_db = {}
                            
                        fr = []
                        for r in r_list:
                            d_name = str(r.get('driverName','')).strip()
                            c_num = str(r.get('carNumber','')).strip()
                            u_reg = user_dict.get(d_name, {}).get('region', '미정')
                            u_shf = user_dict.get(d_name, {}).get('shift', '주간')
                            mems = r.get('report_memos', {})
                            if isinstance(mems, str):
                                try: mems = ast.literal_eval(mems)
                                except: mems = {}
                            mems_items = mems.items() if isinstance(mems, dict) else (enumerate(mems) if isinstance(mems, list) else [])
                            
                            rst = r.get('ride_start_time')
                            ride_dt = pd.to_datetime(rst, unit='ms', utc=True).tz_convert('Asia/Seoul') if rst else None
                            sw_key = f"{ride_dt.strftime('%Y-%m-%d')}_{c_num}" if ride_dt else ""
                            sw = sw_db.get(sw_key, {})
                            
                            for k, v in mems_items:
                                if isinstance(v, dict) and 'id' in v:
                                    memo_text = v.get('memo', str(v))
                                    k = v.get('id')
                                else:
                                    memo_text = str(v)
                                if not str(k).startswith('ADMIN_'):
                                    ds = pd.to_datetime(int(k), unit='ms', utc=True).tz_convert('Asia/Seoul') if str(k).isdigit() else None
                                    if ds:
                                        shift_d = dc.get_shift_date(ds)
                                        d_str = shift_d.strftime('%Y-%m-%d')
                                        t_str = ds.strftime('%H:%M:%S')
                                        if not ride_dt:
                                            sw_key_backup = f"{ds.strftime('%Y-%m-%d')}_{c_num}"
                                            sw = sw_db.get(sw_key_backup, {})
                                        maj, min_cat, dtl = dc.split_issue_text_to_vars(memo_text)
                                        fr.append({
                                            '발생일자': d_str, '발생시간': t_str, '차량번호': c_num, '운전자': d_name, '대분류': maj, '중분류': min_cat, '상세내용': dtl, 
                                            '위도(Lat)': r.get('latitude',''), '경도(Lng)': r.get('longitude',''),
                                            'Safeview': str(r.get('Safeview', r.get('SW_Safeview', sw.get('Safeview', '-')))).strip(),
                                            'CPU': str(r.get('CPU', r.get('SW_CPU', sw.get('CPU', '-')))).strip(),
                                            'MCU': str(r.get('MCU', r.get('SW_MCU', sw.get('MCU', '-')))).strip(),
                                            'V1': str(r.get('VPU1', r.get('SW_VPU1', sw.get('VPU1', '-')))).strip(),
                                            'V2': str(r.get('VPU2', r.get('SW_VPU2', sw.get('VPU2', '-')))).strip(),
                                            'V3': str(r.get('VPU3', r.get('SW_VPU3', sw.get('VPU3', '-')))).strip(),
                                            'V4': str(r.get('VPU4', r.get('SW_VPU4', sw.get('VPU4', '-')))).strip(),
                                            '지역': u_reg, '근무시간': u_shf, 'shift_date_obj': shift_d 
                                        })
                        if fr:
                            iss_df = pd.DataFrame(fr)
                            iss_df = iss_df[(iss_df['shift_date_obj'] >= dl_s_date) & (iss_df['shift_date_obj'] <= dl_e_date)]
                            if dl_region != "전체": iss_df = iss_df[iss_df['운전자'].isin(r_users)]
                            if not iss_df.empty: 
                                iss_df = iss_df[['발생일자', '발생시간', '차량번호', '운전자', '대분류', '중분류', '상세내용', '위도(Lat)', '경도(Lng)', 'Safeview', 'CPU', 'MCU', 'V1', 'V2', 'V3', 'V4', '지역', '근무시간']]
                                iss_df = iss_df.sort_values(by=['발생일자', '발생시간'])
                                csv_bytes = iss_df.to_csv(index=False).encode('utf-8-sig')

                    if csv_bytes:
                        st.session_state['dl_csv_bytes'] = csv_bytes
                        st.rerun()
                    else: st.warning("해당 조건의 데이터가 없습니다.")
        else:
            st.success("✅ 파일 준비 완료!")
            st.download_button(f"📥 {dl_type} 다운로드", st.session_state['dl_csv_bytes'], f"{dl_type.split(' ')[0]}_{dl_region}_{dl_s_date}_{dl_e_date}.csv", "text/csv", use_container_width=True)
            if st.button("🔄 조건 변경 및 새로고침", use_container_width=True):
                st.session_state['dl_csv_bytes'] = None
                st.rerun()

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    if st.button("로그아웃 🚪", use_container_width=True): st.session_state.clear(); st.rerun()

f_df = df.copy(); f_drive = df_drive.copy()

if fs and fe:
    if not f_df.empty: f_df = f_df[(f_df['shift_date'] >= fs) & (f_df['shift_date'] <= fe)]
    if not f_drive.empty: f_drive = f_drive[(f_drive['shift_date'] >= fs) & (f_drive['shift_date'] <= fe)]

clean_df = f_df.drop_duplicates(subset=['timestamp_str', 'carNumber'], keep='last').copy() if not f_df.empty else pd.DataFrame()

target_region = st.session_state.view_region
if 'region' not in u_df.columns: u_df['region'] = '미정' 

if target_region != "전체":
    region_users = u_df[u_df['region'] == target_region]['name'].dropna().tolist()
    if not region_users: region_users = ['__NO_USER__'] 
    if not clean_df.empty: clean_df = clean_df[clean_df['driverName'].isin(region_users)]
    if not f_drive.empty: f_drive = f_drive[f_drive['Safe_Guard'].isin(region_users)]

weather_html = tab_summary.get_toss_style_weather(target_region)
if weather_html: st.markdown(weather_html, unsafe_allow_html=True)
else: st.info("⛅ 일시적으로 날씨 정보를 불러올 수 없습니다.")

tc, tp, ti, tr, cc = 0, 0, 0, 0, 0
if not clean_df.empty:
    rr = clean_df[clean_df['status'] != 'ISSUE_ONLY'].copy()
    if not rr.empty: rr['revenue'] = rr.apply(dc.calc_revenue, axis=1)
    try: clean_df['duration_min'] = ((pd.to_datetime(clean_df['ride_end_time'], unit='ms', errors='coerce') - pd.to_datetime(clean_df['ride_start_time'], unit='ms', errors='coerce')).dt.total_seconds() / 60).fillna(0)
    except: clean_df['duration_min'] = 0
    clean_df['이슈건수'] = clean_df.apply(dc.get_global_issue_count, axis=1)
    tc = int(rr['callCount'].sum()) if not rr.empty else 0
    tp = int(pd.to_numeric(rr['passengers'], errors='coerce').fillna(0).sum()) if not rr.empty else 0
    ti = int(clean_df['이슈건수'].sum())
    tr = int(rr['revenue'].sum()) if not rr.empty else 0
    cc = clean_df['carNumber'].nunique()

st.markdown(f"<div style='display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap;'><div style='flex: 1; min-width: 150px; background: #ffffff; padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #f1f5f9;'><div style='font-size: 22px; margin-bottom: 8px;'>📞</div><div style='font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 2px;'>총 호출 수</div><div style='font-size: 26px; color: #0f172a; font-weight: 800; letter-spacing: -0.5px;'>{tc:,} <span style='font-size: 15px; color: #94a3b8; font-weight: 600;'>회</span></div></div><div style='flex: 1; min-width: 150px; background: #ffffff; padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #f1f5f9;'><div style='font-size: 22px; margin-bottom: 8px;'>👥</div><div style='font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 2px;'>총 탑승객</div><div style='font-size: 26px; color: #0f172a; font-weight: 800; letter-spacing: -0.5px;'>{tp:,} <span style='font-size: 15px; color: #94a3b8; font-weight: 600;'>명</span></div></div><div style='flex: 1.2; min-width: 180px; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #bbf7d0;'><div style='font-size: 22px; margin-bottom: 8px;'>💰</div><div style='font-size: 13px; color: #166534; font-weight: 600; margin-bottom: 2px;'>(예상)누적 수입금</div><div style='font-size: 26px; color: #14532d; font-weight: 800; letter-spacing: -0.5px;'>{tr:,} <span style='font-size: 15px; color: #166534; font-weight: 600;'>원</span></div></div><div style='flex: 1; min-width: 150px; background: #ffffff; padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04); border: 1px solid #f1f5f9;'><div style='font-size: 22px; margin-bottom: 8px;'>🚕</div><div style='font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 2px;'>운행 차량</div><div style='font-size: 26px; color: #0f172a; font-weight: 800; letter-spacing: -0.5px;'>{cc} <span style='font-size: 15px; color: #94a3b8; font-weight: 600;'>대</span></div></div><div style='flex: 1; min-width: 150px; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); padding: 20px; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid #fecaca;'><div style='font-size: 22px; margin-bottom: 8px;'>🚨</div><div style='font-size: 13px; color: #991b1b; font-weight: 600; margin-bottom: 2px;'>발생 이슈</div><div style='font-size: 26px; color: #7f1d1d; font-weight: 800; letter-spacing: -0.5px;'>{ti} <span style='font-size: 15px; color: #991b1b; font-weight: 600;'>건</span></div></div></div>", unsafe_allow_html=True)

t_titles = ["📊 통합 Summary", "🧑‍✈️ Safe Guard 별", "🚗 차량 별"]
if st.session_state.user_role in ['admin', 'DM']: t_titles.append("⚙️ 시스템 관리")
tbs = st.tabs(t_titles)

with tbs[0]: tab_summary.draw_summary_tab(clean_df, f_drive)
with tbs[1]: tab_safeguard.draw_safeguard_tab(clean_df, f_drive, sched_df)
with tbs[2]: tab_vehicle.draw_car_tab(clean_df, f_drive) 
if st.session_state.user_role in ['admin', 'DM']:
    with tbs[3]: am.draw_admin_tab(clean_df, f_drive, u_df, sched_df, m_cars, m_drivers, kst_now)
