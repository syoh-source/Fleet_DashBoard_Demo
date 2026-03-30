import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import pydeck as pdk
import re 
import firebase_manager as fm

# 페이지 설정
st.set_page_config(layout="wide", page_title="누적 탑승현황", page_icon="🚖")

# ==========================================
# 🔐 1. 세션 상태 초기화 (로그인 정보 관리)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'settings_unlocked' not in st.session_state:
    st.session_state.settings_unlocked = False

# ==========================================
# 🚪 2. 화면 분기 (로그인 전 vs 로그인 후)
# ==========================================

if not st.session_state.logged_in:
    # ---------------- [A. 로그인 전: 로그인/회원가입 화면] ----------------
    st.title("🚖 탑승 데이터 대시보드")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입 (승인 요청)"])
        
        with tab_login:
            # 폼을 사용하지 않고 직접 입력 받아 리런 오류 방지
            u_id = st.text_input("아이디 (이메일 주소)", key="main_login_id")
            u_pw = st.text_input("비밀번호", type="password", key="main_login_pw")
            
            if st.button("로그인 🚀", use_container_width=True):
                success, user_data, msg = fm.authenticate_user(u_id, u_pw)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_data['role']
                    st.session_state.user_name = user_data['name']
                    st.success(f"✅ {user_data['name']}님 환영합니다! 잠시만 기다려주세요...")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(msg)
                        
        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                new_id = st.text_input("희망 아이디 (이메일 주소)")
                new_pw = st.text_input("비밀번호 (4자리 이상)", type="password")
                new_name = st.text_input("이름 (실명)")
                new_position = st.text_input("직책 / 소속")
                if st.form_submit_button("가입 신청하기 📝", use_container_width=True):
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not new_id or not new_pw or not new_name:
                        st.warning("필수 항목을 입력하세요.")
                    elif not re.match(email_pattern, new_id):
                        st.warning("이메일 형식이 아닙니다.")
                    elif len(new_pw) < 4:
                        st.warning("비밀번호가 너무 짧습니다.")
                    else:
                        success, msg = fm.create_user(new_id, new_pw, new_name, new_position)
                        if success: st.success(msg)
                        else: st.error(msg)

else:
    # ---------------- [B. 로그인 후: 메인 대시보드 화면] ----------------
    
    st.title("🚖 Ride Count Dashboard")

    # 사이드바 설정
    st.sidebar.success(f"👤 **{st.session_state.user_name}**님 환영합니다! ({st.session_state.user_role.upper()})")

    # 관리자 알림 (승인 대기자 체크)
    if st.session_state.user_role == 'admin':
        all_users = fm.get_all_users()
        pending_count = sum(1 for u in all_users if not u.get('is_approved', False))
        if pending_count > 0:
            st.sidebar.warning(f"🚨 승인 대기 회원이 **{pending_count}명** 있습니다!")

    if st.sidebar.button("로그아웃 🚪", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.session_state.user_name = None
        st.session_state.settings_unlocked = False
        st.rerun()

    st.sidebar.divider()

    # --- 데이터 로드 및 전처리 ---
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

    # 사이드바 필터 설정
    st.sidebar.header("⚙️ 관제 필터")
    auto_refresh = st.sidebar.checkbox("🔄 실시간 자동 새로고침 (5초)")
    min_date = df['date'].min() if not df.empty else kst_now.date()
    max_date = df['date'].max() if not df.empty else kst_now.date()
    selected_date = st.sidebar.date_input("날짜 범위", value=(min_date, max_date))
    use_all_time = st.sidebar.checkbox("⏰ 전체 시간 검색", value=True)
    tc1, tc2 = st.sidebar.columns(2)
    with tc1: start_time = st.time_input("시작", value=datetime.time(0, 0), disabled=use_all_time)
    with tc2: end_time = st.time_input("종료", value=datetime.time(23, 59), disabled=use_all_time)

    selected_cars = st.sidebar.multiselect("차량 번호", sorted(master_cars), default=[])
    selected_drivers = st.sidebar.multiselect("운전자 이름", sorted(master_drivers), default=[])

    # 필터링 로직
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

    # 탭 구성
    tabs = st.tabs(["📊 누적 현황", "⚙️ 관리자 설정"]) if st.session_state.user_role == "admin" else st.tabs(["📊 누적 현황"])

    # --- 탭 1: 누적 현황 ---
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

    # --- 탭 2: 관리자 설정 (어드민 전용) ---
    if st.session_state.user_role == "admin":
        with tabs[1]:
            if not st.session_state.settings_unlocked:
                st.warning("🔒 관리자 설정에 접근하려면 2차 비밀번호가 필요합니다.")
                pw = st.text_input("관리자 전용 비밀번호", type="password", key="admin_unlock_pw")
                if st.button("잠금 해제 🔓"):
                    if pw == "0105*":
                        st.session_state.settings_unlocked = True
                        st.rerun()
                    else: st.error("비밀번호가 틀렸습니다.")
            else:
                col_title, col_btn = st.columns([4, 1])
                with col_title: st.subheader("⚙️ 관리자 대시보드")
                with col_btn: 
                    if st.button("🚪 안전하게 나가기 (잠금)", use_container_width=True):
                        st.session_state.settings_unlocked = False
                        st.rerun()
                st.divider()
                
                # 회원 관리 섹션
                st.markdown("### 👥 회원 권한 관리")
                user_list = fm.get_all_users()
                if user_list:
                    u_df = pd.DataFrame(user_list)
                    edit_u = u_df[['user_id', 'name', 'position', 'role', 'is_approved']].copy()
                    edit_u.insert(0, '🗑️ 삭제', False)
                    edit_u.rename(columns={'user_id':'ID', 'name':'이름', 'position':'직책', 'role':'권한', 'is_approved':'승인완료'}, inplace=True)
                    
                    edited_u = st.data_editor(edit_u, hide_index=True, use_container_width=True, disabled=['ID', '이름', '직책', '권한'])
                    if st.button("💾 회원 권한 저장 적용", type="primary"):
                        for _, row in edited_u.iterrows():
                            if row['🗑️ 삭제']: fm.delete_user(row['ID'])
                            else: fm.update_user_approval(row['ID'], row['승인완료'])
                        st.success("회원 정보 업데이트 완료!")
                        time.sleep(1); st.rerun()

                st.divider()
                # 마스터 데이터 섹션
                st.markdown("### 🚗 마스터 데이터 관리")
                mc1, mc2 = st.columns(2)
                with mc1:
                    e_cars = st.data_editor(pd.DataFrame(master_cars, columns=['차량번호']), num_rows="dynamic", use_container_width=True, key="ce")
                with mc2:
                    e_drivers = st.data_editor(pd.DataFrame(master_drivers, columns=['기사이름']), num_rows="dynamic", use_container_width=True, key="de")
                if st.button("💾 마스터 데이터 덮어쓰기 저장", type="primary"):
                    fm.update_master_data(e_cars['차량번호'].dropna().tolist(), e_drivers['기사이름'].dropna().tolist())
                    st.success("데이터 저장 완료!"); time.sleep(1); st.rerun()

                st.divider()
                # 로그 관리 섹션
                st.markdown("### 🗄️ 운행기록 상세 관리")
                if not filtered_df.empty:
                    all_sel = st.checkbox("✅ 일괄 선택 (삭제용)")
                    e_log = filtered_df[['doc_id', 'timestamp', 'carNumber', 'driverName', 'callCount', 'passengers', 'remark']].copy()
                    e_log.insert(0, '🗑️ 삭제', all_sel)
                    e_log.rename(columns={'timestamp':'시간','carNumber':'차량','driverName':'기사','callCount':'호출','passengers':'탑승객','remark':'📝 비고'}, inplace=True)
                    edited_log = st.data_editor(e_log, hide_index=True, use_container_width=True, disabled=['시간','차량','기사','호출','탑승객'])
                    if st.button("💾 기록 변경사항 저장", type="primary"):
                        for _, row in edited_log.iterrows():
                            if row['🗑️ 삭제']: fm.delete_ride_log(row['doc_id'])
                            elif e_log.loc[_, '📝 비고'] != row['📝 비고']: fm.update_ride_remark(row['doc_id'], row['📝 비고'])
                        st.success("처리 완료!"); time.sleep(1); st.rerun()

    # 실시간 자동 새로고침
    if auto_refresh:
        time.sleep(5)
        st.rerun()
