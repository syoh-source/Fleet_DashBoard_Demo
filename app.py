import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import pydeck as pdk
import re # 🌟 이메일 형식 검사를 위한 정규식 라이브러리 추가
import firebase_manager as fm

st.set_page_config(layout="wide", page_title="누적 탑승현황", page_icon="🚖")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['name'] = None
if 'settings_unlocked' not in st.session_state:
    st.session_state['settings_unlocked'] = False

# ==========================================
# 🚪 1. 로그인 및 회원가입 화면
# ==========================================
if not st.session_state['logged_in']:
    st.title("🚖 탑승 데이터 대시보드")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입 (승인 요청)"])
        
        with tab_login:
            with st.form("login_form"):
                user_id = st.text_input("아이디 (이메일 주소)")
                user_pw = st.text_input("비밀번호", type="password")
                submit_login = st.form_submit_button("로그인 🚀", use_container_width=True)
                
                if submit_login:
                    success, user_data, msg = fm.authenticate_user(user_id, user_pw)
                    if success:
                        st.session_state['logged_in'] = True
                        st.session_state['role'] = user_data['role']
                        st.session_state['name'] = user_data['name']
                        st.rerun()
                    else:
                        st.error(msg)
                        
        with tab_signup:
            with st.form("signup_form"):
                new_id = st.text_input("희망 아이디 (이메일 주소)")
                new_pw = st.text_input("비밀번호 (4자리 이상, 숫자/특수문자 포함 가능)", type="password")
                new_name = st.text_input("이름 (실명)")
                new_position = st.text_input("직책 / 소속")
                submit_signup = st.form_submit_button("가입 신청하기 📝", use_container_width=True)
                
                if submit_signup:
                    # 🌟 이메일 형식 검증 패턴
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    
                    if not new_id or not new_pw or not new_name:
                        st.warning("아이디, 비밀번호, 이름은 필수 입력입니다.")
                    elif not re.match(email_pattern, new_id):
                        st.warning("⚠️ 아이디는 올바른 이메일 형식이어야 합니다. (예: user@swm.ai)")
                    elif len(new_pw) < 4:
                        st.warning("⚠️ 비밀번호는 최소 4자리 이상이어야 합니다.")
                    else:
                        success, msg = fm.create_user(new_id, new_pw, new_name, new_position)
                        if success: st.success(msg)
                        else: st.error(msg)
    st.stop()

# ==========================================
# 🚀 2. 메인 대시보드
# ==========================================
st.title("🚖 Ride Count Dashboard")

st.sidebar.success(f"👤 **{st.session_state['name']}**님 환영합니다! ({st.session_state['role'].upper()})")

if st.session_state['role'] == 'admin':
    all_users = fm.get_all_users()
    pending_count = sum(1 for u in all_users if not u.get('is_approved', False))
    if pending_count > 0:
        st.sidebar.warning(f"🚨 승인 대기 중인 신규 회원이 **{pending_count}명** 있습니다! 설정 탭을 확인하세요.")

if st.sidebar.button("로그아웃 🚪", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

@st.cache_data(ttl=60)
def cached_weather(): return fm.get_gangnam_weather()
weather_info = cached_weather()
if weather_info:
    st.markdown("##### 📍 강남구 실시간 날씨 (기상청API)")
    w_col1, w_col2, w_col3, w_col4, w_col5 = st.columns(5)
    with w_col1: st.metric("기온", f"{weather_info.get('T1H', '-')} ℃")
    with w_col2: st.metric("날씨 상태", "비/눈" if weather_info.get('PTY', '0') != '0' else "맑음/흐림")
    with w_col3: st.metric("1시간 강수량", f"{weather_info.get('RN1', '-')} mm")
    with w_col4: st.metric("습도", f"{weather_info.get('REH', '-')} %")
    with w_col5: st.metric("풍속", f"{weather_info.get('WSD', '-')} m/s")
    st.divider()

doc_ref, master_data = fm.get_master_data()
master_cars, master_drivers = master_data.get('cars', []), master_data.get('drivers', [])

raw_data = fm.get_ride_logs()
df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()
kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')

if not df.empty and 'timestamp' in df.columns:
    df['datetime_obj'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Seoul')
    df['timestamp'] = df['datetime_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['date'] = df['datetime_obj'].dt.date
    df = df.sort_values(by='datetime_obj', ascending=False)
else:
    df['date'], df['datetime_obj'] = kst_now.date(), kst_now

st.sidebar.header("⚙️ 관제 필터")
auto_refresh = st.sidebar.checkbox("🔄 실시간 자동 새로고침 켜기 (5초)")
min_date = df['date'].min() if not df.empty else kst_now.date()
max_date = df['date'].max() if not df.empty else kst_now.date()
selected_date = st.sidebar.date_input("날짜 범위", value=(min_date, max_date))
use_all_time = st.sidebar.checkbox("⏰ 전체 시간 검색", value=True)
tc1, tc2 = st.sidebar.columns(2)
with tc1: start_time = st.time_input("시작", value=datetime.time(0, 0), disabled=use_all_time)
with tc2: end_time = st.time_input("종료", value=datetime.time(23, 59), disabled=use_all_time)

selected_cars = st.sidebar.multiselect("차량 번호", sorted(master_cars), default=[])
selected_drivers = st.sidebar.multiselect("운전자 이름", sorted(master_drivers), default=[])

filtered_df = df.copy()
if not filtered_df.empty:
    real_start_time, real_end_time = (datetime.time(0,0,0), datetime.time(23,59,59)) if use_all_time else (start_time, end_time)
    start_date = end_date = selected_date[0] if len(selected_date) == 1 else selected_date[0]
    if len(selected_date) == 2: start_date, end_date = selected_date
    if start_date == end_date and real_start_time > real_end_time: end_date += datetime.timedelta(days=1)
    
    start_dt = pd.Timestamp(datetime.datetime.combine(start_date, real_start_time)).tz_localize('Asia/Seoul')
    end_dt = pd.Timestamp(datetime.datetime.combine(end_date, real_end_time)).tz_localize('Asia/Seoul')
    filtered_df = filtered_df[(filtered_df['datetime_obj'] >= start_dt) & (filtered_df['datetime_obj'] <= end_dt)]
    if selected_cars: filtered_df = filtered_df[filtered_df['carNumber'].isin(selected_cars)]
    if selected_drivers: filtered_df = filtered_df[filtered_df['driverName'].isin(selected_drivers)]

tabs = st.tabs(["📊 누적 현황", "⚙️ 관리자 설정"]) if st.session_state['role'] == "admin" else st.tabs(["📊 누적 현황"])

# ----------------- [관제 대시보드 (공통)] -----------------
with tabs[0]:
    if filtered_df.empty: st.warning("데이터가 없습니다.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("데이터 건수", f"{len(filtered_df)} 건")
        c2.metric("탑승객 수", f"{filtered_df['passengers'].sum()} 명")
        c3.metric("운행 차량", f"{filtered_df['carNumber'].nunique()} 대")

        st.divider()
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**🚗 차량별 누적 탑승객 수**")
            chart1 = alt.Chart(filtered_df.groupby('carNumber')['passengers'].sum().reset_index()).mark_bar(color="#4CAF50").encode(x='carNumber', y='passengers').properties(height=300)
            st.altair_chart(chart1, use_container_width=True)
        with cc2:
            st.markdown("**⏰ 시간대별 데이터 건수**")
            filtered_df['hour'] = filtered_df['datetime_obj'].dt.hour
            chart2 = alt.Chart(filtered_df.groupby('hour').size().reset_index(name='count')).mark_bar(color="#2196F3").encode(x='hour:O', y='count').properties(height=300)
            st.altair_chart(chart2, use_container_width=True)

        st.divider()
        st.subheader("🗺️ 실시간 탑승 위치 (Heatmap points)")
        map_df = filtered_df.dropna(subset=['latitude', 'longitude']).copy()
        if not map_df.empty:
            map_df['latitude'] = pd.to_numeric(map_df['latitude'], errors='coerce')
            map_df['longitude'] = pd.to_numeric(map_df['longitude'], errors='coerce')
            map_df = map_df.dropna(subset=['latitude', 'longitude'])
            if not map_df.empty:
                view_state = pdk.ViewState(latitude=map_df['latitude'].mean(), longitude=map_df['longitude'].mean(), zoom=14, pitch=0)
                layer = pdk.Layer("ScatterplotLayer", data=map_df, get_position="[longitude, latitude]", get_fill_color="[255, 140, 0, 150]", get_radius=20, pickable=True)
                st.pydeck_chart(pdk.Deck(map_style=None, initial_view_state=view_state, layers=[layer]))
            else: st.info("유효한 위치 데이터가 없습니다.")
        else: st.info("GPS 데이터가 없습니다.")

    if auto_refresh:
        time.sleep(5)
        st.rerun()

# ----------------- [관리자 설정 (어드민 전용)] -----------------
if st.session_state['role'] == "admin":
    with tabs[1]:
        if not st.session_state['settings_unlocked']:
            st.warning("🔒 관리자 설정에 접근하려면 2차 비밀번호가 필요합니다.")
            # 🌟 관리자 탭 2차 잠금 비밀번호도 0105* 로 변경!
            pw = st.text_input("관리자 전용 비밀번호", type="password")
            if st.button("잠금 해제 🔓"):
                if pw == "1234":
                    st.session_state['settings_unlocked'] = True
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
        else:
            col_title, col_btn = st.columns([4, 1])
            with col_title: st.subheader("⚙️ 관리자 대시보드")
            with col_btn: 
                if st.button("🚪 안전하게 나가기 (잠금)", use_container_width=True):
                    st.session_state['settings_unlocked'] = False
                    st.rerun()
            
            st.divider()
            
            st.markdown("### 👥 회원 가입 및 권한 관리")
            st.info("💡 '승인 완료' 체크박스를 누르고 **[회원 권한 저장]**을 눌러야 접속이 가능해집니다. '영구 삭제' 체크 시 가입 내역이 지워집니다.")
            
            user_df = pd.DataFrame(all_users)
            if not user_df.empty:
                edit_user = user_df[['user_id', 'name', 'position', 'role', 'is_approved']].copy()
                edit_user.insert(0, '🗑️ 영구 삭제', False)
                edit_user.rename(columns={'user_id':'아이디(이메일)', 'name':'이름', 'position':'직책', 'role':'권한', 'is_approved':'✅ 승인 완료'}, inplace=True)
                
                edited_users = st.data_editor(
                    edit_user, hide_index=True, use_container_width=True, 
                    disabled=['아이디(이메일)', '이름', '직책', '권한']
                )
                
                if st.button("💾 회원 권한 저장 적용", type="primary"):
                    for idx, row in edited_users.iterrows():
                        uid = row['아이디(이메일)']
                        if row['🗑️ 영구 삭제']: fm.delete_user(uid)
                        else: fm.update_user_approval(uid, row['✅ 승인 완료'])
                    st.success("✅ 회원 정보가 성공적으로 업데이트되었습니다!")
                    time.sleep(1)
                    st.rerun()
            else:
                st.write("등록된 회원이 없습니다.")
                
            st.divider()
            
            st.markdown("### 🚗 마스터 데이터 관리 (일괄 편집)")
            st.info("💡 표 맨 아래 빈칸을 눌러 새 항목을 추가하거나, 휴지통 아이콘을 눌러 삭제한 뒤 **[데이터베이스 덮어쓰기]**를 누르세요.")
            
            mc1, mc2 = st.columns(2)
            with mc1:
                st.write("#### 차량 리스트")
                edited_cars = st.data_editor(pd.DataFrame(master_cars, columns=['차량번호']), num_rows="dynamic", use_container_width=True, key="car_editor")
            with mc2:
                st.write("#### 기사 리스트")
                edited_drivers = st.data_editor(pd.DataFrame(master_drivers, columns=['기사이름']), num_rows="dynamic", use_container_width=True, key="driver_editor")
                
            if st.button("💾 마스터 데이터 덮어쓰기 (저장)", type="primary"):
                new_car_list = edited_cars['차량번호'].dropna().tolist()
                new_driver_list = edited_drivers['기사이름'].dropna().tolist()
                fm.update_master_data(new_car_list, new_driver_list)
                st.success("✅ 차량/기사 리스트가 서버에 안전하게 덮어쓰기 되었습니다!")
                time.sleep(1)
                st.rerun()

            st.divider()
            
            st.markdown("### 🗄️ 운행기록 일괄 삭제 및 수정")
            if not filtered_df.empty:
                select_all = st.checkbox("✅ 아래 보이는 모든 기록 일괄 선택 (삭제용)")
                edit_log = filtered_df[['doc_id', 'timestamp', 'carNumber', 'driverName', 'callCount', 'passengers', 'remark']].copy()
                edit_log.insert(0, '🗑️ 삭제', select_all)
                edit_log.rename(columns={'timestamp':'시간', 'carNumber':'차량', 'driverName':'기사', 'callCount':'호출', 'passengers':'탑승객', 'remark':'📝 비고'}, inplace=True)

                edited_logs = st.data_editor(edit_log, hide_index=True, use_container_width=True, disabled=['시간', '차량', '기사', '호출', '탑승객'])

                if st.button("💾 운행 기록 변경사항 서버에 적용", type="primary"):
                    changes, deletes = 0, 0
                    for index, row in edited_logs.iterrows():
                        tid = row['doc_id']
                        if row['🗑️ 삭제']:
                            fm.delete_ride_log(tid)
                            deletes += 1
                        elif edit_log.loc[index, '📝 비고'] != row['📝 비고']:
                            fm.update_ride_remark(tid, row['📝 비고'])
                            changes += 1
                    if changes > 0 or deletes > 0:
                        st.success(f"✅ 서버 처리 완료! (수정: {changes}건, 삭제: {deletes}건)")
                        time.sleep(1)
                        st.rerun()
                    else: st.warning("변경된 항목이 없습니다.")
            else:
                st.warning("왼쪽 필터에 해당하는 검색 결과가 없습니다.")
