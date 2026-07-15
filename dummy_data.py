import pandas as pd
import datetime

def generate_dummy_data():
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
        d_logs.append({'timestamp': dt.replace(hour=8), '날짜': dt.strftime('%Y-%m-%d'), '차량번호': car, 'Safe_Guard': drv, '출발자': drv, '종료자': '', '유형': '출발', '출발_km': 15000+i*100, '출발_배터리_차량': 100})
        d_logs.append({'timestamp': dt.replace(hour=17), '날짜': dt.strftime('%Y-%m-%d'), '차량번호': car, 'Safe_Guard': drv, '출발자': '', '종료자': drv, '유형': '종료', '종료_km': 15000+i*100+95, '종료_배터리_차량': 30, '총주행거리(km)': 95, '특이사항': '특이사항 없음'})
        
    s_logs = []
    for i in range(14):
        dt = now - datetime.timedelta(days=i)
        for j in range(5):
            s_logs.append({'date': dt.strftime('%Y-%m-%d'), 'name': m_drivers[j], 'type': f"배정({m_cars[(i+j)%5]})"})
            
    return {'m_cars': m_cars, 'm_drivers': m_drivers, 'u_df': u_df, 'df': pd.DataFrame(r_logs), 'df_drive': pd.DataFrame(d_logs), 'sched_df': pd.DataFrame(s_logs)}
