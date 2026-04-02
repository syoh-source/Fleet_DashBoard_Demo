import os
os.environ["GRPC_DNS_RESOLVER"] = "native"
os.environ["GRPC_POLL_STRATEGY"] = "epoll1"

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

    # 🌟 [수정됨] 에러를 화면에 뱉어내는 포획망이 적용된 상태창
    with st.status("🔄 파이어베이스 데이터 동기화 중...", expanded=False) as status:
        try:
            st.write("⏳ 1. 마스터 데이터(차량/기사) 요청 중...")
            _, master_data = fm.get_master_data()
            if master_data is None: master_data = {'cars': [], 'drivers': []}
            st.write("✅ 1. 마스터 데이터 로드 완료!")
            m_cars = master_data.get('cars', [])
            m_drivers = master_data.get('drivers', [])

            st.write("⏳ 2. 운행 기록(Logs) 데이터 요청 중...")
            logs = fm.get_ride_logs()
            if logs is None: logs = []
            st.write(f"✅ 2. 운행 기록 {len(logs)}건 로드 완료!")
            df = pd.DataFrame(logs)
            status.update(label="✅ 모든 데이터 로드 완료!", state="complete", expanded=False)
        except Exception as e:
            st.error(f"🚨 파이어베이스 통신 중 에러 발생: {e}")
            status.update(label="❌ 데이터 로드 실패 (에러 확인)", state="error", expanded=True)
            st.stop()

    kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')
    if not df.empty:
        df['timestamp_safe'] = df['timestamp'].astype(str)
        df['dt_obj'] = pd.to_datetime(df['timestamp_safe'], errors='coerce', utc=True).dt.tz_convert('Asia/Seoul')
        if df['dt_obj'].isnull().any(): df['dt_obj'] = df['dt_obj'].fillna(kst_now)
        df['timestamp_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df['date'] = df['dt_obj'].dt.date
        df = df.sort_values(by='dt_obj', ascending=False)
    else:
        # 🌟 [수정됨] 완벽한 빈 도화지 (기둥만 세우기)
        df = pd.DataFrame(columns=[
            'timestamp', 'timestamp_safe', 'timestamp_str', 'date', 'dt_obj', 
            'carNumber', 'driverName', 'passengers', 'callCount', 
            'remark', 'weather', 'latitude', 'longitude'
        ])

    # --- 사이드바 설정 영역 ---
    st.sidebar.header("⚙️ 대시보드 설정")
    
    st.sidebar.subheader("📍 날씨 관측 기준")
    weather_source_car = st.sidebar.selectbox(
        "기준 차량 선택", 
        ["자동(최신순)"] + sorted(m_cars),
        help="선택한 차량이 현장에서 보고한 날씨를 상단에 표시합니다."
    )

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

    # --- 실시간 현장 날씨 섹션 ---
    st.markdown(f"##### 🛰️ 실시간 현장 날씨 관제")
    
    today_str = kst_now.strftime('%Y-%m-%d')
    if not df.empty and 'timestamp_str' in df.columns:
        w_df = df[df['timestamp_str'].str.contains(today_str, na=False)].copy()
    else:
        w_df = pd.DataFrame()

    if weather_source_car != "자동(최신순)" and not w_df.empty:
        w_df = w_df[w_df['carNumber'] == weather_source_car]

    if not w_df.empty and 'weather' in w_df.columns:
        current_w = w_df.iloc[0] 
        raw_weather = current_w['weather']
        
        try:
            cond = raw_weather.split(',')[0].strip()
            temp = raw_weather.split(',')[1].split('℃')[0].strip() if '℃' in raw_weather else "-"
        except:
            cond = "분석중"; temp = "-"

        w_col = st.columns([1, 1, 1, 1.5])
        w_col[0].metric("현재 기온", f"{temp} ℃")
        w_col[1].metric("기상 상태", cond)
        w_col[2].metric("기준 차량", current_w['carNumber'])
        w_col[3].metric("최종 수신 시각", current_w['timestamp_str'].split(' ')[1])
        
        st.caption(f"📢 **현장 리포트:** {raw_weather}")
    else:
        st.info(f"📌 {weather_source_car if weather_source_car != '자동(최신순)' else '운행'} 차량의 오늘 날씨 데이터가 아직 없습니다.")

    if st.button("🔄 현장 날씨 즉시 새로고침", use_container_width=True):
        st.rerun()
    st.divider()

    # --- 데이터 필터링 로직 ---
    f_df = df.copy()
    if not f_df.empty:
        sd = sel_date[0] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 0 else sel_date
        ed = sel_date[1] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 1 else sd
        f_df = f_df[(f_df['date'] >= sd) & (f_df['date'] <= ed)]
        if sel_cars: f_df = f_df[f_df['carNumber'].isin(sel_cars)]
        if sel_drivers: f_df = f_df[f_df['driverName'].isin(sel_drivers)]

    # 🌟 [수정됨] 엑셀 탭 에러 방지용 빈 통 만들기
    if f_df.empty:
        clean_df = pd.DataFrame(columns=f_df.columns if not f_df.empty else [])
    else:
        clean_df = f_df.drop_duplicates(subset=['date', 'carNumber', 'callCount'], keep='last').copy()

    tabs = st.tabs(["📊 누적 현황", "⚙️ 관리자 설정"]) if st.session_state.user_role == 'admin' else st.tabs(["📊 누적 현황"])

    with tabs[0]:
        # 🌟 [수정됨] 데이터 없을 때 깔끔하게 경고창만 띄우기
        if clean_df.empty:
            st.warning("⚠️ 표시할 운행 데이터가 없습니다.")
        else:
            total_calls = len(clean_df)
            clean_df['passengers'] = pd.to_numeric(clean_df['passengers'], errors='coerce').fillna(0)
            total_passengers = int(clean_df['passengers'].sum())

            m1, m2, m3 = st.columns(3)
            m1.metric("총 호출 수", f"{total_calls} 회")
            m2.metric("총 탑승객 수", f"{total_passengers} 명")
            m3.metric("운행 차량", f"{clean_df['carNumber'].nunique()} 대")
            
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**🚗 차량별 탑승객 누적**")
                car_df = clean_df.groupby('carNumber')['passengers'].sum().reset_index()
                st.altair_chart(alt.Chart(car_df).mark_bar(color="#4CAF50").encode(
                    x=alt.X('carNumber:N', axis=alt.Axis(labelAngle=0)), 
                    y='passengers:Q'
                ), use_container_width=True)
            with cc2:
                st.markdown("**⏰ 구간별 운행 건수 (요금표 기준)**")
                def get_time_bracket(h):
                    if 4 <= h < 22: return "04~22시(4,800원)"
                    elif h == 22: return "22~23시(5,800원)"
                    elif h in [23, 0, 1]: return "23~02시(6,700원)"
                    elif h in [2, 3]: return "02~04시(5,800원)"
                    return "기타"

                # 🌟 [수정됨] 차트 시간 속성 에러 방지
                clean_df['dt_obj'] = pd.to_datetime(clean_df['dt_obj'], errors='coerce')
                clean_df['hour'] = clean_df['dt_obj'].dt.hour
                clean_df['time_bracket'] = clean_df['hour'].apply(get_time_bracket)
                bracket_df = clean_df.groupby('time_bracket').size().reset_index(name='count')
                bracket_order = ["04~22시(4,800원)", "22~23시(5,800원)", "23~02시(6,700원)", "02~04시(5,800원)"]
                
                st.altair_chart(alt.Chart(bracket_df).mark_bar(color="#2196F3").encode(
                    x=alt.X('time_bracket:N', sort=bracket_order, axis=alt.Axis(labelAngle=0, title='요금 적용 시간대')), 
                    y=alt.Y('count:Q', title='운행 건수')
                ), use_container_width=True)

            st.divider(); st.subheader("🗺️ 탑승 위치")
            map_df = clean_df.copy()
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
                    st.pydeck_chart(pdk.Deck(map_style="road", initial_view_state=v_state, layers=[pt_layer], tooltip={"html": "<b>🚗 {carNumber}</b> <br/> 탑승: {passengers}명"}))
                else:
                    st.info("📌 유효한 GPS 좌표가 없습니다.")

            st.divider()
            final_df = clean_df.rename(columns={'carNumber': 'fleet', 'driverName': 'driver', 'callCount': 'call', 'remark': '비고(메모)'})
            disp = [c for c in ['timestamp_str', 'fleet', 'driver', 'call', 'passengers', 'latitude', 'longitude', 'weather', '비고(메모)'] if c in final_df.columns]
            
            total_items = len(final_df)
            items_per_page = 100
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

            col_title, col_page = st.columns([3, 1])
            with col_title:
                st.subheader("📋 상세 탑승 기록")
                st.caption(f"총 **{total_items}**건의 기록이 있습니다.")
            with col_page:
                page_num = st.number_input("페이지", min_value=1, max_value=total_pages, value=1, step=1) if total_pages > 1 else 1

            start_idx = (page_num - 1) * items_per_page
            st.dataframe(final_df[disp].iloc[start_idx:start_idx+items_per_page], use_container_width=True)

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
                if st.button("💾 마스터 데이터 저장"):
                    fm.update_master_data(ec['차량번호'].dropna().tolist(), ed['기사이름'].dropna().tolist())
                    st.success("저장 완료"); time.sleep(0.5); st.rerun()

                st.divider(); st.markdown("### 🗄️ 운행 기록 상세 관리 (엑셀 모드)")
                if not clean_df.empty:
                    edit_df = clean_df[['doc_id', 'timestamp_str', 'carNumber', 'driverName', 'callCount', 'passengers', 'remark']].copy()
                    select_all = st.checkbox("✅ 전체 기록 삭제 선택 (초기화용)")
                    edit_df.insert(0, '🗑️ 삭제', select_all) 
                    edit_df = edit_df.rename(columns={'timestamp_str': '시간', 'carNumber': '차량', 'driverName': '기사', 'callCount': '호출', 'passengers': '탑승객', 'remark': '📝 비고'})
                    edited_df = st.data_editor(edit_df, hide_index=True, use_container_width=True, disabled=['시간', '차량', '기사', '호출', '탑승객'], column_config={"doc_id": None})
                    
                    if st.button("💾 기록 일괄 저장"):
                        deleted_count = 0
                        for idx, row in edited_df.iterrows():
                            if row['🗑️ 삭제']: 
                                fm.delete_ride_log(row['doc_id'])
                                deleted_count += 1
                            elif edit_df.loc[idx, '📝 비고'] != row['📝 비고']: 
                                fm.update_ride_remark(row['doc_id'], row['📝 비고'])
                        st.success(f"🧹 {deleted_count}건 삭제 및 처리 완료!"); time.sleep(1); st.rerun()

    if auto_refresh:
        time.sleep(10)
        st.rerun()
