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

    # [중요] 미국 서버 차단 방지를 위해 기상청 API 직접 호출은 여기서 제거했습니다.
    with st.status("데이터 동기화 진행 중...", expanded=False) as status:
        _, master_data = fm.get_master_data()
        m_cars = master_data.get('cars', [])
        m_drivers = master_data.get('drivers', [])

        logs = fm.get_ride_logs()
        df = pd.DataFrame(logs)
        status.update(label="✅ 모든 데이터 로드 완료!", state="complete", expanded=False)

    kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')
    if not df.empty:
        df['timestamp_safe'] = df['timestamp'].astype(str)
        df['dt_obj'] = pd.to_datetime(df['timestamp_safe'], errors='coerce', utc=True).dt.tz_convert('Asia/Seoul')
        if df['dt_obj'].isnull().any(): df['dt_obj'] = df['dt_obj'].fillna(kst_now)
        df['timestamp_str'] = df['dt_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df['date'] = df['dt_obj'].dt.date
        df = df.sort_values(by='dt_obj', ascending=False)
    else:
        df = pd.DataFrame(columns=['date', 'dt_obj', 'carNumber', 'driverName', 'passengers', 'callCount', 'remark', 'weather'])
        df.loc[0, 'date'] = kst_now.date()

    # --- 사이드바 설정 ---
    st.sidebar.header("⚙️ 대시보드 설정")
    
    # 🌟 날씨 기준 차량 선택 (사장님 요청 반영)
    st.sidebar.subheader("📍 날씨 관측 기준")
    weather_source_car = st.sidebar.selectbox(
        "날씨 기준 차량 선택", 
        ["자동(최신순)"] + sorted(m_cars)
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

    f_df = df.copy()
    if not f_df.empty:
        sd = sel_date[0] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 0 else sel_date
        ed = sel_date[1] if isinstance(sel_date, (tuple, list)) and len(sel_date) > 1 else sd
        f_df = f_df[(f_df['date'] >= sd) & (f_df['date'] <= ed)]
        if sel_cars: f_df = f_df[f_df['carNumber'].isin(sel_cars)]
        if sel_drivers: f_df = f_df[f_df['driverName'].isin(sel_drivers)]

    # --- 메인 화면: 실시간 날씨 관제 섹션 ---
    st.markdown(f"##### 🛰️ 실시간 현장 날씨 관제")
    
    # 오늘 날짜의 날씨 데이터만 추출
    today_str = kst_now.strftime('%Y-%m-%d')
    w_df = df[df['timestamp_str'].str.contains(today_str)].copy()

    if weather_source_car != "자동(최신순)":
        w_df = w_df[w_df['carNumber'] == weather_source_car]

    if not w_df.empty:
        current_w = w_df.iloc[0] 
        raw_weather = current_w.get('weather', '정보 없음')
        
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
        st.info(f"📌 {weather_source_car} 차량의 오늘 날씨 데이터가 아직 없습니다.")
    
    st.divider()

    tabs = st.tabs(["📊 누적 현황", "⚙️ 관리자 설정"]) if st.session_state.user_role == 'admin' else st.tabs(["📊 누적 현황"])

    with tabs[0]:
        if f_df.empty: st.warning("표시할 데이터가 없습니다.")
        else:
            # 중복 제거 (set 방식 도입 전 과거 데이터 대응)
            clean_df = f_df.drop_duplicates(subset=['date', 'carNumber', 'callCount'], keep='last').copy()
            
            daily_max_df = clean_df.groupby(['date', 'carNumber'])[['callCount', 'passengers']].max().reset_index()
            total_calls = int(daily_max_df['callCount'].sum()) if not daily_max_df.empty else 0
            total_passengers = int(daily_max_df['passengers'].sum()) if not daily_max_df.empty else 0

            m1, m2, m3 = st.columns(3)
            m1.metric("총 호출 수", f"{total_calls} 회")
            m2.metric("총 탑승객 수", f"{total_passengers} 명")
            m3.metric("운행 차량", f"{clean_df['carNumber'].nunique()} 대")
            
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
                def get_time_bracket(h):
                    if 4 <= h < 22: return "04~22시(4.8k)"
                    elif h == 22: return "22~23시(5.8k)"
                    elif h in [23, 0, 1]: return "23~02시(6.7k)"
                    elif h in [2, 3]: return "02~04시(5.8k)"
                    return "기타"

                clean_df['hour'] = clean_df['dt_obj'].dt.hour
                clean_df['time_bracket'] = clean_df['hour'].apply(get_time_bracket)
                bracket_df = clean_df.groupby('time_bracket').size().reset_index(name='count')
                bracket_order = ["04~22시(4.8k)", "22~23시(5.8k)", "23~02시(6.7k)", "02~04시(5.8k)"]
                
                st.altair_chart(alt.Chart(bracket_df).mark_bar(color="#2196F3").encode(
                    x=alt.X('time_bracket:N', sort=bracket_order, axis=alt.Axis(labelAngle=0, title='요금 시간대')), 
                    y=alt.Y('count:Q', title='운행 건수')
                ), use_container_width=True)

            st.divider(); st.subheader("🗺️ 탑승 위치")
            map_data = clean_df.dropna(subset=['latitude', 'longitude']).copy()
            if not map_data.empty:
                v_state = pdk.ViewState(
                    latitude=float(map_data['latitude'].mean()), 
                    longitude=float(map_data['longitude'].mean()), 
                    zoom=13
                )
                st.pydeck_chart(pdk.Deck(
                    map_style="road", 
                    initial_view_state=v_state, 
                    layers=[pdk.Layer("ScatterplotLayer", data=map_data, get_position="[longitude, latitude]", get_fill_color="[220, 20, 60, 200]", get_radius=30, pickable=True)],
                    tooltip={"html": "<b>🚗 {carNumber}</b><br/>탑승: {passengers}명"}
                ))

            st.divider()
            # 페이지네이션
            final_df = clean_df.rename(columns={'carNumber': 'fleet', 'driverName': 'driver', 'callCount': 'call', 'remark': '비고'})
            disp = ['timestamp_str', 'fleet', 'driver', 'call', 'passengers', 'weather', '비고']
            
            total_items = len(final_df)
            items_per_page = 100
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

            cp1, cp2 = st.columns([3, 1])
            cp1.subheader("📋 상세 탑승 기록")
            page_num = cp2.number_input("페이지", 1, total_pages, 1) if total_pages > 1 else 1
            st.dataframe(final_df[disp].iloc[(page_num-1)*100 : page_num*100], use_container_width=True)

    if st.session_state.user_role == 'admin':
        with tabs[1]:
            if not st.session_state.settings_unlocked:
                pw = st.text_input("2차 비밀번호", type="password")
                if st.button("잠금 해제 🔓"):
                    if pw == "1234": st.session_state.settings_unlocked = True; st.rerun()
                    else: st.error("불일치")
            else:
                if st.button("🚪 설정 닫기"): st.session_state.settings_unlocked = False; st.rerun()
                
                # 회원 승인
                st.markdown("### 👥 회원 승인 관리")
                u_df = pd.DataFrame(fm.get_all_users())
                if not u_df.empty:
                    u_edit = st.data_editor(u_df[['user_id', 'name', 'position', 'is_approved']].copy().assign(삭제=False), hide_index=True)
                    if st.button("💾 회원 데이터 저장"):
                        for _, r in u_edit.iterrows():
                            if r['삭제']: fm.delete_user(r['user_id'])
                            else: fm.update_user_approval(r['user_id'], r['is_approved'])
                        st.rerun()

                # 마스터 관리
                st.divider(); st.markdown("### 🚗 차량 및 안전요원 관리")
                mc1, mc2 = st.columns(2)
                ec = mc1.data_editor(pd.DataFrame(m_cars, columns=['차량번호']), num_rows="dynamic")
                ed = mc2.data_editor(pd.DataFrame(m_drivers, columns=['이름']), num_rows="dynamic")
                if st.button("💾 마스터 저장"):
                    fm.update_master_data(ec['차량번호'].dropna().tolist(), ed['이름'].dropna().tolist())
                    st.rerun()

                # 일괄 삭제
                st.divider(); st.markdown("### 🗄️ 기록 일괄 관리")
                if not f_df.empty:
                    select_all = st.checkbox("✅ 전체 선택 (초기화용)")
                    edit_df = f_df[['doc_id', 'timestamp_str', 'carNumber', 'callCount', 'remark']].copy()
                    edit_df.insert(0, '🗑️ 삭제', select_all)
                    edited_df = st.data_editor(edit_df, hide_index=True, use_container_width=True)
                    if st.button("💾 기록 일괄 처리"):
                        for _, row in edited_df.iterrows():
                            if row['🗑️ 삭제']: fm.delete_ride_log(row['doc_id'])
                        st.success("처리 완료!"); time.sleep(1); st.rerun()

    if auto_refresh:
        time.sleep(10)
        st.rerun()
