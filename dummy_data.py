import pandas as pd
import random
from datetime import datetime, timedelta, timezone

def get_demo_data():
    # 1. 마스터 정보 세팅
    m_cars = ["E100#1", "E100#2", "E100#3"]
    m_drivers = ["정재훈", "이철수", "김준", "최영희"]
    
    u_df = pd.DataFrame([
        {"name": "정재훈", "region": "상암", "shift": "주간 (08:00~17:30)"},
        {"name": "이철수", "region": "강남", "shift": "주간 (08:00~17:30)"},
        {"name": "김준", "region": "상암", "shift": "야간 (18:00~03:00)"},
        {"name": "최영희", "region": "강남", "shift": "야간 (18:00~03:00)"}
    ])
    
    # 2. 15일치 더미 데이터 동적 생성 (현재 시간 기준 15일 전부터)
    KST = timezone(timedelta(hours=9))
    base_date = datetime(2026, 7, 6, tzinfo=KST)
    
    df_data = []       # 탑승(콜) 기록
    df_drive_data = [] # 출퇴근 운행 일지
    
    # 차량별 누적 주행거리 트래커
    km_tracker = {"E100#1": 40000, "E100#2": 52000, "E100#3": 15000}
    
    for i in range(15): 
        current_date = base_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # ==========================================
        # ☀️ 주간조 세팅 (08:00 ~ 17:30)
        # ==========================================
        day_drivers = ["정재훈", "이철수"]
        day_cars = ["E100#1", "E100#3"]
        
        for d_idx, driver in enumerate(day_drivers):
            car = day_cars[d_idx]
            start_time = current_date.replace(hour=8, minute=0)
            start_km = km_tracker[car]
            
            # (1) 주간 출발 기록
            df_drive_data.append({
                "id": f"start_{date_str}_{driver}", "유형": "출발", 
                "차량번호": car, "Safe_Guard": driver, # 원본 DB 규격 엄수
                "출발_장소": "차고지", "출발_km": start_km,
                "출발_배터리_차량": random.randint(90, 100), "날짜": date_str,
                "timestamp": start_time.isoformat()
            })
            
            # (2) 주간 콜(운행) 기록 (하루 6~12건 생성)
            num_rides = random.randint(6, 12)
            ride_start = start_time + timedelta(minutes=random.randint(10, 30))
            for r in range(num_rides):
                ride_end = ride_start + timedelta(minutes=random.randint(10, 40))
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver,
                    "callCount": random.choices([1, 2], weights=[80, 20])[0],
                    "passengers": random.randint(1, 4), "status": "완료"
                })
                ride_start = ride_end + timedelta(minutes=random.randint(5, 20))
            
            # (3) 주간 종료 기록
            end_time = current_date.replace(hour=17, minute=30)
            drive_dist = random.randint(80, 150)
            end_km = start_km + drive_dist
            km_tracker[car] = end_km
            
            df_drive_data.append({
                "id": f"end_{date_str}_{driver}", "유형": "종료", 
                "차량번호": car, "Safe_Guard": driver,
                "종료_장소": "차고지", "종료_km": end_km, "총주행거리(km)": drive_dist, 
                "종료_배터리_차량": random.randint(20, 50), "날짜": date_str, 
                "timestamp": end_time.isoformat(), "특이사항": "이상 없음"
            })

        # ==========================================
        # 🌙 야간조 세팅 (18:00 ~ 익일 03:00)
        # ==========================================
        night_drivers = ["김준", "최영희"]
        night_cars = ["E100#1", "E100#2"]
        
        for d_idx, driver in enumerate(night_drivers):
            car = night_cars[d_idx]
            start_time = current_date.replace(hour=18, minute=0)
            start_km = km_tracker[car]
            
            # (1) 야간 출발 기록
            df_drive_data.append({
                "id": f"start_{date_str}_night_{driver}", "유형": "출발", 
                "차량번호": car, "Safe_Guard": driver,
                "출발_장소": "교대거점", "출발_km": start_km,
                "출발_배터리_차량": random.randint(80, 100), "날짜": date_str,
                "timestamp": start_time.isoformat()
            })
            
            # (2) 야간 콜(운행) 기록 (하루 5~15건 생성)
            num_rides = random.randint(5, 15)
            ride_start = start_time + timedelta(minutes=random.randint(10, 30))
            for r in range(num_rides):
                ride_end = ride_start + timedelta(minutes=random.randint(15, 45))
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver,
                    "callCount": random.choices([1, 2], weights=[70, 30])[0],
                    "passengers": random.randint(1, 3), "status": "완료"
                })
                ride_start = ride_end + timedelta(minutes=random.randint(10, 30))
            
            # (3) 야간 종료 기록 (날짜가 다음날로 넘어감)
            end_time = (current_date + timedelta(days=1)).replace(hour=3, minute=0)
            drive_dist = random.randint(100, 200)
            end_km = start_km + drive_dist
            km_tracker[car] = end_km
            
            df_drive_data.append({
                "id": f"end_{date_str}_night_{driver}", "유형": "종료", 
                "차량번호": car, "Safe_Guard": driver,
                "종료_장소": "차고지", "종료_km": end_km, "총주행거리(km)": drive_dist, 
                "종료_배터리_차량": random.randint(10, 40), 
                "날짜": end_time.strftime("%Y-%m-%d"), 
                "timestamp": end_time.isoformat(), "특이사항": "야간 특이사항 없음"
            })

    return {
        'm_cars': m_cars,
        'm_drivers': m_drivers,
        'u_df': u_df,
        'df': pd.DataFrame(df_data),
        'df_drive': pd.DataFrame(df_drive_data),
        'sched_df': pd.DataFrame([])
    }
