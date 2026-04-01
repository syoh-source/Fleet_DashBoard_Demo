import streamlit as st
import pandas as pd
import altair as alt
import time
import datetime
import pydeck as pdk
import firebase_manager as fm

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="운행 데이터 관제 시스템", page_icon="🚖")

if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_role': None, 'user_name': None, 'settings_unlocked': False})

if not st.session_state.logged_in:
    st.title("🚖 Ride Count Dashboard")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_signup = st.tabs(["🔑 로그인", "📝 회원가입 (승인 요청)"])
        with tab_login:
            u_id = st.text_input("아이디 (이메일 주소)", key="main_login_id")
            u_pw = st.text_input("비밀번호", type="password", key="main_login_pw")
            if st.button("로그인 🚀", use_container_width=True):
                if u_id and u_pw:
                    with st.spinner("서버 연결 확인 중..."):
                        success, user_data, msg = fm.authenticate_user(u_id, u_pw)
                    if success:
                        st.session_state.update({'logged_in': True, 'user_role': user_data['role'], 'user_name': user_data['name']})
                        st.rerun()
                    else: st.error(msg)
                else: st.warning("아이디와 비밀번호를 입력하세요.")
                        
        with tab_signup:
            with st.form("signup_form", clear_on_submit=True):
                new_id = st.text_input("희망 아이디 (이메일)")
                new_pw = st.text_input("비밀번호 (4자리 이상)", type="password")
                new_name = st.text_input("이름 (실명)")
                new_position = st.text_input("직책 / 소속")
                if st.form_submit_button("가입 신청 📝", use_container_width=True):
                    if not new_id or not new_pw or not new_name: st.warning("필수 항목 입력!")
                    else:
                        s, m = fm.create_user(new_id, new_pw, new_name, new_position)
                        if s: st.success(m)
                        else: st.error(m)
    st.stop()

else:
    if st.sidebar.button("로그아웃 🚪", use_container_width=True):
        st.session_state.clear(); st.rerun()

    st.title("🚖 Fleet Dashboard (자율주행 택시)")
    st.sidebar.success(f"👤 **{st.session_state.user_name}**님 ({st.session_state.user_role.upper()})")

    with st.status("데이터 동기화 진행 중...", expanded=False) as status:
        @st.cache_data(ttl=60)
        def cached_weather(): return fm.get_gangnam_weather()
        weather_info = cached_weather()
        
        _, master_data = fm.get_master_data()
        m_cars = master_data.get('cars', [])
        m_drivers = master_data.get('drivers', [])

        logs = fm.get_ride_logs()
        df = pd.DataFrame(logs)
        status.update(label="✅ 모든 데이터 로드 완료!", state="complete", expanded=False)

    if weather_info:
        st.markdown("##### 📍 강남구 실시간 날씨 (기상청API)")
        w_col = st.columns(5)
        w_col[0].metric("기온", f"{weather_info.get('T1H', '-')} ℃")
        w_col[1].metric("상태", "비/눈" if weather_info.get('PTY', '0') != '0' else "맑음/흐림")
        w_col[2].metric("강수", f"{weather_info.get('RN1', '-')} mm")
        w_col[3].metric("습도", f"{weather_info.get('REH', '-')} %")
        w_col[4].metric("풍속", f"{weather_info.get('WSD', '-')} m/s")
        st.divider()

    kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')
    if not df.empty:
        df['timestamp_safe'] = df['timestamp'].astype(str)
        df['dt_obj'] = pd.to_datetime(df['timestamp_safe'], errors='coerce', utc=True).dt.tz_convert('Asia/Seoul')
        if df['dt_obj'].isnull().any(): df['dt_obj'] = df['dt_obj'].fillna(kst_now)
        df['timestamp_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df['date'] = df['dt_obj'].dt.date
        df = df.sort_values(by='dt_obj', ascending=False)
    else:
        df = pd.DataFrame(columns=['date', 'dt_obj', 'carNumber', 'driverName', 'passengers', 'callCount', 'remark'])
        df.loc[0, 'date'] = kst_now.date()

    st.sidebar.header("⚙️ 대시보드 설정")
    if st.sidebar.button("🔄 데이터 수동 새로고침", use_container_width=True):
        st.rerun()
        
    auto_refresh = st.sidebar.checkbox("🔄 자동 새로고침 켜기 (10초)", value=False)
    
    st.sidebar.divider()
    st.sidebar.header("🔍 검색 필터")
    min_d, max_d = (df['date'].min(), df['date'].max()) if not df.empty else (kst_now.date(), kst_now.date())
    sel_date = st.sidebar.date_input("날짜 범위", value=(min_d, max_d))
    use_all_time = st.sidebar.checkbox("⏰ 전체 시간 검색", value=True)
    
    tc1, tc2 = st.sidebar.columns(2)
    s_t = tc1.time_input("시작", value=datetime.time(0, 0), disabled=use_all_time)
    e_t = tc2.time_input("종료", value=datetime.time(23, 59), disabled=use_all_time)

    sel_cars = st.sidebar.multiselect("차량 번호", sorted(m_cars))
    sel_drivers = st.sidebar.multiselect("운전자 이름", sorted(m_drivers))

    f_df = df.copy()
    if not f_df.empty:
        sd = sel_date[0] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 0 else sel_date
        ed = sel_date[1] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 1 else sd
        f_df = f_df[(f_df['date'] >= sd) & (f_df['date'] <= ed)]
        if sel_cars: f_df = f_df[f_df['carNumber'].isin(sel_cars)]
        if sel_drivers: f_df = f_df[f_df['driverName'].isin(sel_drivers)]

    tabs = st.tabs(["📊 누적 현황", "⚙️ 관리자 설정"]) if st.session_state.user_role == 'admin' else st.tabs(["📊 누적 현황"])

    with tabs[0]:
        if f_df.empty: st.warning("표시할 데이터가 없습니다.")
        else:
            daily_max_df = f_df.groupby(['date', 'carNumber'])[['callCount', 'passengers']].max().reset_index()
            total_calls = int(daily_max_df['callCount'].sum()) if not daily_max_df.empty else 0
            total_passengers = int(daily_max_df['passengers'].sum()) if not daily_max_df.empty else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("총 호출 수", f"{total_calls} 회")
            m2.metric("총 탑승객 수", f"{total_passengers} 명")
            m3.metric("운행 차량", f"{f_df['carNumber'].nunique()} 대")
            
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**🚗 차량별 탑승객 누적**")
                car_df = daily_max_df.groupby('carNumber')['passengers'].sum().reset_index()
                st.altair_chart(alt.Chart(car_df).mark_bar(color="#4CAF50").encode(
                    x=alt.X('carNumber:N', axis=alt.Axis(labelAngle=0)), 
                    y='passengers:Q'
                ), use_container_width=True)
            with cc2:
                st.markdown("**⏰ 구간별 운행 건수 (요금표 기준)**")
                
                # 🌟 사장님 맞춤형: 시간에 따라 4개의 요금 구간으로 묶어주는 함수
                def get_time_bracket(h):
                    if 4 <= h < 22:
                        return "04~22시(4,800원)"
                    elif h == 22:
                        return "22~23시(5,800원)"
                    elif h in [23, 0, 1]:
                        return "23~02시(6,700원)"
                    elif h in [2, 3]:
                        return "02~04시(5,800원)"
                    return "기타"

                f_df['hour'] = f_df['dt_obj'].dt.hour
                f_df['time_bracket'] = f_df['hour'].apply(get_time_bracket)
                
                bracket_df = f_df.groupby('time_bracket').size().reset_index(name='count')
                
                # 🌟 시간 흐름에 맞게 막대그래프 순서 강제 고정
                bracket_order = ["04~22시", "22~23시", "23~02시", "02~04시"]
                
                st.altair_chart(alt.Chart(bracket_df).mark_bar(color="#2196F3").encode(
                    x=alt.X('time_bracket:N', sort=bracket_order, axis=alt.Axis(labelAngle=0, title='요금 적용 시간대')), 
                    y=alt.Y('count:Q', title='운행 건수')
                ), use_container_width=True)

            st.divider(); st.subheader("🗺️ 탑승 위치")
            map_df = f_df.copy()
            if 'latitude' in map_df.columns and 'longitude' in map_df.columns:
                map_df['latitude'] = pd.to_numeric(map_df['latitude'], errors='coerce')
                map_df['longitude'] = pd.to_numeric(map_df['longitude'], errors='coerce')
                map_df = map_df.dropna(subset=['latitude', 'longitude'])
                
                if not map_df.empty:
                    clean_map_df = map_df[['latitude', 'longitude', 'carNumber', 'driverName', 'passengers']].copy()
                    v_state = pdk.ViewState(
                        latitude=float(clean_map_df['latitude'].mean()), 
                        longitude=float(clean_map_df['longitude'].mean()), 
                        zoom=14, pitch=0
                    )
                    pt_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=clean_map_df,
                        get_position="[longitude, latitude]",
                        get_fill_color="[220, 20, 60, 200]", 
                        get_radius=20,
                        pickable=True
                    )
                    st.pydeck_chart(pdk.Deck(
                        map_style="road", 
                        initial_view_state=v_state, 
                        layers=[pt_layer], 
                        tooltip={"html": "<b>🚗 {carNumber} ({driverName})</b> <br/> 탑승: {passengers}명"}
                    ))
                else:
                    st.info("📌 현재 유효한 GPS 좌표가 없어 지도를 표시할 수 없습니다.")
            else:
                st.info("📌 위치 데이터 컬럼을 찾을 수 없습니다.")

            # 🌟 [추가됨] 상세 탑승 기록 100개 단위 페이지네이션
            st.divider()
            
            final_df = f_df.rename(columns={'carNumber': 'fleet', 'driverName': 'driver', 'callCount': 'call', 'remark': '비고(메모)'})
            disp = [c for c in ['timestamp_str', 'fleet', 'driver', 'call', 'passengers', 'latitude', 'longitude', 'weather', '비고(메모)'] if c in final_df.columns]
            
            total_items = len(final_df)
            items_per_page = 100
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

            col_title, col_page = st.columns([3, 1])
            with col_title:
                st.subheader("📋 상세 탑승 기록")
                st.caption(f"총 **{total_items}**건의 기록이 있습니다.")
            with col_page:
                if total_pages > 1:
                    page_num = st.number_input("페이지 번호", min_value=1, max_value=total_pages, value=1, step=1)
                else:
                    page_num = 1

            start_idx = (page_num - 1) * items_per_page
            end_idx = start_idx + items_per_page
            
            # 필터링 및 페이징이 완료된 데이터프레임 표시
            st.dataframe(final_df[disp].iloc[start_idx:end_idx], use_container_width=True)

    if st.session_state.user_role == 'admin':
        with tabs[1]:
            if not st.session_state.settings_unlocked:
                pw = st.text_input("2차 비밀번호", type="password")
                if st.button("잠금 해제 🔓"):
                    if pw == "1234": st.session_state.settings_unlocked = True; st.rerun()
                    else: st.error("불일치")
            else:
                if st.button("🚪 설정 닫기"): st.session_state.settings_unlocked = False; st.rerun()
                st.markdown("### 👥 회원 승인 관리")
                u_df = pd.DataFrame(fm.get_all_users())
                if not u_df.empty:
                    u_edit = u_df[['user_id', 'name', 'position', 'is_approved']].copy()
                    u_edit.insert(0, '🗑️ 삭제', False)
                    edited_u = st.data_editor(u_edit, hide_index=True, use_container_width=True)
                    if st.button("💾 회원 데이터 저장"):
                        for _, r in edited_u.iterrows():
                            if r['🗑️ 삭제']: fm.delete_user(r['user_id'])
                            else: fm.update_user_approval(r['user_id'], r['is_approved'])
                        st.success("저장 완료"); time.sleep(0.5); st.rerun()

                st.divider(); st.markdown("### 🚗 차량 및 안전요원 관리")
                mc1, mc2 = st.columns(2)
                ec = mc1.data_editor(pd.DataFrame(m_cars, columns=['차량번호']), num_rows="dynamic", key="admin_ec")
                ed = mc2.data_editor(pd.DataFrame(m_drivers, columns=['기사이름']), num_rows="dynamic", key="admin_ed")
                if st.button("💾 데이터 저장"):
                    fm.update_master_data(ec['차량번호'].dropna().tolist(), ed['기사이름'].dropna().tolist())
                    st.success("저장 완료"); time.sleep(0.5); st.rerun()

                st.divider(); st.markdown("### 🗄️ 운행 기록 상세 관리 (엑셀 모드)")
                if not f_df.empty:
                    edit_df = f_df[['doc_id', 'timestamp_str', 'carNumber', 'driverName', 'callCount', 'passengers', 'remark']].copy()
                    
                    # 🌟 [추가됨] 마법의 전체 선택 체크박스!
                    select_all = st.checkbox("✅ 전체 기록 삭제 선택 (초기화용)")
                    
                    # select_all이 켜지면 전부 True, 꺼지면 전부 False로 일괄 적용됩니다.
                    edit_df.insert(0, '🗑️ 삭제', select_all) 
                    
                    edit_df = edit_df.rename(columns={'timestamp_str': '시간', 'carNumber': '차량', 'driverName': '기사', 'callCount': '호출', 'passengers': '탑승객', 'remark': '📝 비고'})
                    edited_df = st.data_editor(edit_df, hide_index=True, use_container_width=True, disabled=['시간', '차량', '기사', '호출', '탑승객'], column_config={"doc_id": None, "🗑️ 삭제": st.column_config.CheckboxColumn("🗑️ 삭제", default=False), "📝 비고": st.column_config.TextColumn("📝 비고")})
                    
                    if st.button("💾 기록 저장"):
                        deleted_count = 0
                        for idx, row in edited_df.iterrows():
                            if row['🗑️ 삭제']: 
                                fm.delete_ride_log(row['doc_id'])
                                deleted_count += 1
                            elif edit_df.loc[idx, '📝 비고'] != row['📝 비고']: 
                                fm.update_ride_remark(row['doc_id'], row['📝 비고'])
                                
                        st.success(f"🧹 총 {deleted_count}건 삭제 및 기록 처리 완료!"); time.sleep(1); st.rerun()

    if auto_refresh:
        time.sleep(10)
        st.rerun()
