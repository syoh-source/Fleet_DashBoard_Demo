import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import altair as alt
import time
import datetime

st.set_page_config(layout="wide", page_title="자율주행 택시 대시보드", page_icon="🚖")

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.title("🚖 Fleet Dashboard (자율주행 택시)")

# ==========================================
# 1. 마스터 데이터 및 운행 기록 불러오기
# ==========================================
doc_ref = db.collection('settings').document('master_data')
doc = doc_ref.get()

if doc.exists:
    master_data = doc.to_dict()
else:
    master_data = {'cars': ["자율택시 01호", "자율택시 02호"], 'drivers': ["홍길동", "임꺽정"]}
    doc_ref.set(master_data)

master_cars = master_data.get('cars', [])
master_drivers = master_data.get('drivers', [])

def load_data():
    docs = db.collection('ride_logs').stream()
    data_list = []
    for doc in docs:
        item = doc.to_dict()
        item['doc_id'] = doc.id 
        if 'remark' not in item: item['remark'] = ""
        if 'callCount' not in item: item['callCount'] = 0
        if 'passengers' not in item: item['passengers'] = 0
        data_list.append(item)
    return data_list

raw_data = load_data()

df = pd.DataFrame(raw_data) if raw_data else pd.DataFrame()

# 🌟 1. 현재 한국 시간(KST)을 확실하게 구합니다.
kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')

if not df.empty and 'timestamp' in df.columns:
    # 🌟 2. 파이어베이스 시간(UTC)을 한국 시간(KST)으로 강력하게 강제 변환합니다!
    df['datetime_obj'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('Asia/Seoul')
    df['timestamp'] = df['datetime_obj'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df['date'] = df['datetime_obj'].dt.date
    df = df.sort_values(by='datetime_obj', ascending=False)
else:
    # 데이터가 없을 때도 한국 시간 기준으로 '오늘'을 잡습니다.
    df['date'] = kst_now.date()
    df['datetime_obj'] = kst_now

# ==========================================
# 2. 글로벌 사이드바 필터
# ==========================================
st.sidebar.header("⚙️ 대시보드 설정")
auto_refresh = st.sidebar.checkbox("🔄 실시간 자동 새로고침 켜기 (5초)")

st.sidebar.divider()
st.sidebar.header("🔍 공통 검색 필터")

# 🌟 3. 달력의 기본값도 확실한 한국 시간(KST)으로!
min_date = df['date'].min() if not df.empty else kst_now.date()
max_date = df['date'].max() if not df.empty else kst_now.date()
selected_date = st.sidebar.date_input("날짜 범위를 선택하세요", value=(min_date, max_date), min_value=min_date, max_value=max_date)

use_all_time = st.sidebar.checkbox("⏰ 전체 시간 검색 (00:00 ~ 23:59)", value=True)

time_col1, time_col2 = st.sidebar.columns(2)
with time_col1:
    start_time = st.time_input("시작 시간", value=datetime.time(0, 0), disabled=use_all_time)
with time_col2:
    end_time = st.time_input("종료 시간", value=datetime.time(23, 59), disabled=use_all_time)

st.sidebar.divider()

car_list = sorted(master_cars)
driver_list = sorted(master_drivers)

st.sidebar.info("💡 팁: 목록을 비워두면 '전체'가 검색됩니다.")
selected_cars = st.sidebar.multiselect("차량 번호 (비워두면 전체)", car_list, default=[])
selected_drivers = st.sidebar.multiselect("운전자 이름 (비워두면 전체)", driver_list, default=[])

filtered_df = df.copy()

if not filtered_df.empty:
    if use_all_time:
        real_start_time = datetime.time(0, 0, 0)
        real_end_time = datetime.time(23, 59, 59)
    else:
        real_start_time = start_time
        real_end_time = end_time

    if len(selected_date) == 2:
        start_date, end_date = selected_date
    elif len(selected_date) == 1:
        start_date = selected_date[0]
        end_date = selected_date[0]
    else:
        start_date = end_date = kst_now.date()

    if start_date == end_date and real_start_time > real_end_time:
        end_date = end_date + datetime.timedelta(days=1)

    start_dt = pd.Timestamp(datetime.datetime.combine(start_date, real_start_time)).tz_localize('Asia/Seoul')
    end_dt = pd.Timestamp(datetime.datetime.combine(end_date, real_end_time)).tz_localize('Asia/Seoul')
    
    filtered_df = filtered_df[(filtered_df['datetime_obj'] >= start_dt) & (filtered_df['datetime_obj'] <= end_dt)]

    if selected_cars:
        filtered_df = filtered_df[filtered_df['carNumber'].isin(selected_cars)]
    if selected_drivers:
        filtered_df = filtered_df[filtered_df['driverName'].isin(selected_drivers)]

# ==========================================
# 3. 탭 화면 구성
# ==========================================
tab_dashboard, tab_admin = st.tabs(["📊 관제 대시보드", "⚙️ 관리자 설정"])

with tab_dashboard:
    if filtered_df.empty:
        st.warning("⚠️ 선택하신 조건(차량/운전자/날짜 및 시간)에 해당하는 운행 기록이 없습니다.")
    else:
        st.subheader("📊 운행 요약 (검색 결과)")
        col1, col2, col3 = st.columns(3)
        with col1: st.metric(label="조회된 데이터 건수", value=f"{len(filtered_df)} 건")
        with col2: st.metric(label="조회된 탑승객 수", value=f"{filtered_df['passengers'].sum()} 명")
        with col3: st.metric(label="조회된 운행 차량", value=f"{filtered_df['carNumber'].nunique()} 대")

        st.divider()
        st.subheader("📈 운행 통계 분석")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("**🚗 차량별 누적 탑승객 수**")
            car_df = filtered_df.groupby('carNumber')['passengers'].sum().reset_index()
            car_df.columns = ['차량 번호', '탑승객 수']
            chart1 = alt.Chart(car_df).mark_bar(color="#4CAF50").encode(
                x=alt.X('차량 번호', axis=alt.Axis(labelAngle=0)), y='탑승객 수'
            ).properties(height=300)
            st.altair_chart(chart1, use_container_width=True)
            
        with chart_col2:
            st.markdown("**⏰ 시간대별 데이터 건수**")
            filtered_df['hour'] = filtered_df['datetime_obj'].dt.hour
            hour_df = filtered_df.groupby('hour').size().reset_index()
            hour_df.columns = ['시간대', '데이터 건수']
            chart2 = alt.Chart(hour_df).mark_bar(color="#2196F3").encode(
                x=alt.X('시간대:O', axis=alt.Axis(labelAngle=0)), y='데이터 건수'
            ).properties(height=300)
            st.altair_chart(chart2, use_container_width=True)

        st.divider()
        st.subheader("📋 상세 탑승 기록")
        rename_dict = {'carNumber': 'fleet', 'driverName': 'driver', 'callCount': 'call', 'remark': '비고(메모)'}
        final_df = filtered_df.rename(columns=rename_dict)
        desired_order = ['timestamp', 'fleet', 'driver', 'call', 'passengers', 'latitude', 'longitude', 'weather', '비고(메모)']
        display_cols = [col for col in desired_order if col in final_df.columns]
        final_df = final_df[display_cols]
        st.dataframe(final_df, use_container_width=True)

    if auto_refresh:
        time.sleep(5)
        st.rerun()

with tab_admin:
    st.subheader("⚙️ 마스터 데이터 관리")
    ADMIN_PASSWORD = "1234" 
    entered_pw = st.text_input("🔒 관리자 비밀번호를 입력하세요 (입력 후 Enter)", type="password")
    
    if entered_pw == ADMIN_PASSWORD:
        st.success("✅ 관리자 인증 완료!")
        st.warning("⚠️ 항목을 추가하거나 삭제하실 때는 왼쪽 사이드바의 **[자동 새로고침]을 꼭 끄고** 진행해 주세요!")
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🚗 차량 번호 관리")
            st.dataframe(pd.DataFrame(master_cars, columns=['현재 등록된 차량']), use_container_width=True)
            new_car = st.text_input("➕ 새 차량 추가", key="new_car")
            if st.button("차량 등록하기"):
                if new_car and new_car not in master_cars:
                    master_cars.append(new_car)
                    doc_ref.update({'cars': master_cars})
                    st.success(f"'{new_car}' 등록 완료!")
                    time.sleep(1)
                    st.rerun()
            st.write("") 
            del_car = st.selectbox("🗑️ 삭제할 차량 선택", ["선택 안함"] + master_cars, key="del_car")
            delete_history_car = st.checkbox("⚠️ 이 차량의 과거 운행 기록까지 영구 삭제", key="chk_car")
            if st.button("선택한 차량 삭제"):
                if del_car != "선택 안함" and del_car in master_cars:
                    master_cars.remove(del_car)
                    doc_ref.update({'cars': master_cars})
                    if delete_history_car:
                        docs_to_delete = db.collection('ride_logs').where('carNumber', '==', del_car).stream()
                        for d in docs_to_delete: d.reference.delete()
                    st.success(f"'{del_car}' 삭제 완료!")
                    time.sleep(1)
                    st.rerun()

        with col2:
            st.markdown("#### 👨‍✈️ 기사님 이름 관리")
            st.dataframe(pd.DataFrame(master_drivers, columns=['현재 등록된 기사님']), use_container_width=True)
            new_driver = st.text_input("➕ 새 운전자 추가", key="new_driver")
            if st.button("운전자 등록하기"):
                if new_driver and new_driver not in master_drivers:
                    master_drivers.append(new_driver)
                    doc_ref.update({'drivers': master_drivers})
                    st.success(f"'{new_driver}' 등록 완료!")
                    time.sleep(1)
                    st.rerun()
            st.write("") 
            del_driver = st.selectbox("🗑️ 삭제할 운전자 선택", ["선택 안함"] + master_drivers, key="del_driver")
            delete_history_driver = st.checkbox("⚠️ 이 기사님의 과거 운행 기록까지 영구 삭제", key="chk_driver")
            if st.button("선택한 운전자 삭제"):
                if del_driver != "선택 안함" and del_driver in master_drivers:
                    master_drivers.remove(del_driver)
                    doc_ref.update({'drivers': master_drivers})
                    if delete_history_driver:
                        docs_to_delete = db.collection('ride_logs').where('driverName', '==', del_driver).stream()
                        for d in docs_to_delete: d.reference.delete()
                    st.success(f"'{del_driver}' 삭제 완료!")
                    time.sleep(1)
                    st.rerun()
                    
        st.divider()
        st.markdown("### 🗄️ 운행기록 상세 관리 (엑셀 모드)")
        st.info("💡 **왼쪽 필터**로 조회된 데이터가 아래 표에 나타납니다. **비고(메모)** 칸을 더블클릭해서 글씨를 쓰거나, **삭제** 칸에 체크를 한 뒤 맨 아래 [저장] 버튼을 누르세요!")

        if not filtered_df.empty:
            edit_df = filtered_df[['doc_id', 'timestamp', 'carNumber', 'driverName', 'callCount', 'passengers', 'remark']].copy()
            edit_df.insert(0, '🗑️ 삭제', False)
            edit_df = edit_df.rename(columns={
                'timestamp': '시간',
                'carNumber': '차량',
                'driverName': '기사',
                'callCount': '호출',
                'passengers': '탑승객',
                'remark': '📝 비고'
            })

            edited_df = st.data_editor(
                edit_df,
                hide_index=True,
                use_container_width=True,
                disabled=['시간', '차량', '기사', '호출', '탑승객'],
                column_config={
                    "doc_id": None, 
                    "🗑️ 삭제": st.column_config.CheckboxColumn("🗑️ 삭제", default=False),
                    "📝 비고": st.column_config.TextColumn("📝 비고")
                }
            )

            if st.button("💾 체크 및 변경사항 서버에 적용하기", type="primary"):
                changes = 0
                deletes = 0
                
                for index, row in edited_df.iterrows():
                    target_id = row['doc_id']
                    
                    if row['🗑️ 삭제'] == True:
                        db.collection('ride_logs').document(target_id).delete()
                        deletes += 1
                    else:
                        original_remark = edit_df.loc[index, '📝 비고']
                        new_remark = row['📝 비고']
                        if original_remark != new_remark:
                            db.collection('ride_logs').document(target_id).update({'remark': new_remark})
                            changes += 1
                
                if changes > 0 or deletes > 0:
                    st.success(f"✅ 서버 처리 완료! (메모 수정: {changes}건, 영구 삭제: {deletes}건)")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.warning("변경된 항목이 없습니다.")

        else:
            st.warning("왼쪽 필터에 해당하는 검색 결과가 없습니다.")

    elif entered_pw != "":
        st.error("❌ 비밀번호가 틀렸습니다. 다시 확인해 주세요.")