import pandas as pd

def get_demo_data():
    """
    app.py에서 데모 모드 실행 시 호출하는 함수입니다.
    리턴값은 반드시 m_cars, m_drivers, u_df, df, df_drive, sched_df 키를 가진 딕셔너리여야 합니다.
    """
    
    # 1. 차량 마스터 목록
    m_cars = ["E100#1", "E100#2"]
    
    # 2. 운전자(Safe Guard) 마스터 목록
    m_drivers = ["정재훈", "김준"]
    
    # 3. 사용자 정보 (u_df)
    u_df_data = [
        {"name": "정재훈", "region": "상암", "shift": "주간 (08:00~17:30)"},
        {"name": "김준", "region": "상암", "shift": "주간 (08:00~17:30)"}
    ]
    u_df = pd.DataFrame(u_df_data)
    
    # 4. 운행기록/탑승정보 (df -> app.py에서 clean_df로 변환됨)
    # KeyError 방지를 위해 밀리초(ms) 단위의 ride_start_time, ride_end_time 추가
    df_data = [
        {
            "timestamp": "2026-07-20T11:30:00.000000+00:00", 
            "ride_start_time": 1784514600000, 
            "ride_end_time": 1784515500000, # 15분간 탑승 
            "carNumber": "E100#1", 
            "driverName": "정재훈", 
            "callCount": 1, 
            "passengers": 2,
            "status": "완료"
        },
        {
            "timestamp": "2026-07-20T14:20:00.000000+00:00", 
            "ride_start_time": 1784524800000, 
            "ride_end_time": 1784526000000, # 20분간 탑승
            "carNumber": "E100#1", 
            "driverName": "정재훈", 
            "callCount": 1, 
            "passengers": 1,
            "status": "완료"
        },
        {
            "timestamp": "2026-07-21T13:00:00.000000+00:00", 
            "ride_start_time": 1784606400000, 
            "ride_end_time": 1784608200000, # 30분간 탑승
            "carNumber": "E100#2", 
            "driverName": "김준", 
            "callCount": 2, 
            "passengers": 3,
            "status": "완료"
        }
    ]
    df = pd.DataFrame(df_data)
    
    # 5. 차량 출발/종료 데이터 (df_drive -> app.py에서 f_drive로 변환됨)
    df_drive_data = [
        {
            "출발_장소": "학여울", "timestamp": "2026-07-20T11:00:00.000000+00:00", 
            "출발_배터리_뒤탭": "100", "유형": "출발", "출발_배터리_폰": "100", 
            "차량번호": "E100#1", "Safe_Guard": "정재훈", "출발_배터리_앞탭": "100", 
            "출발_km": 49000, "출발_배터리_차량": "95", "날짜": "2026-07-20", "id": "dummy_start_001"
        },
        {
            "timestamp": "2026-07-20T19:00:00.000000+00:00", "종료_배터리_뒤탭": "100", 
            "종료_배터리_앞탭": "80", "유형": "종료", "차량번호": "E100#1", 
            "Safe_Guard": "정재훈", "종료_km": 49100, "총주행거리(km)": 100, 
            "특이사항": "이상 없음", "종료_장소": "SL", "종료_배터리_폰": "100", 
            "종료_배터리_차량": "40", "날짜": "2026-07-20", "id": "dummy_end_001"
        },
        {
            "출발_장소": "SL", "timestamp": "2026-07-21T12:00:00.000000+00:00", 
            "출발_배터리_뒤탭": "100", "유형": "출발", "출발_배터리_폰": "100", 
            "차량번호": "E100#2", "Safe_Guard": "김준", "출발_배터리_앞탭": "100", 
            "출발_km": 50500, "출발_배터리_차량": "90", "날짜": "2026-07-21", "id": "dummy_start_002"
        },
        {
            "timestamp": "2026-07-21T20:00:00.000000+00:00", "종료_배터리_뒤탭": "100", 
            "종료_배터리_앞탭": "90", "유형": "종료", "차량번호": "E100#2", 
            "Safe_Guard": "김준", "종료_km": 50620, "총주행거리(km)": 120, 
            "특이사항": "우천으로 서행", "종료_장소": "학여울", "종료_배터리_폰": "100", 
            "종료_배터리_차량": "35", "날짜": "2026-07-21", "id": "dummy_end_002"
        }
    ]
    df_drive = pd.DataFrame(df_drive_data)
    
    # 6. 스케줄 (일단 빈 프레임으로 처리)
    sched_df = pd.DataFrame([])
    
    # app.py가 원하는 규격에 맞춰 딕셔너리로 묶어서 리턴
    return {
        'm_cars': m_cars,
        'm_drivers': m_drivers,
        'u_df': u_df,
        'df': df,
        'df_drive': df_drive,
        'sched_df': sched_df
    }
