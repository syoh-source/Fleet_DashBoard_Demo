import pandas as pd
import random
from datetime import datetime, timedelta, timezone

def get_demo_data():
    # 1. 13대 차량 세팅
    m_cars = [f"E100#{i:02d}" for i in range(1, 14)] # E100#01 ~ E100#13
    
    # 2. 26명 운전자 세팅 (주/야간 각 13명)
    day_drivers = ["김민준", "이서준", "박도윤", "최시우", "정지호", "강건우", "조은우", "윤선우", "장서진", "임연우", "한유준", "오하준", "서도현"]
    night_drivers = ["김서연", "이서윤", "박지우", "최지민", "정다은", "강하은", "조하윤", "윤시아", "장지율", "임서현", "한아린", "오채원", "서소율"]
    m_drivers = day_drivers + night_drivers
    
    # 3. 차량/운전자별 지역 배분 (상암 5대, 강남 4대, 안양 4대)
    regions = ["상암"]*5 + ["강남"]*4 + ["안양"]*4
    base_coords = {
        "상암": (37.578, 126.890),
        "강남": (37.498, 127.028),
        "안양": (37.394, 126.922)
    }
    
    u_df_data = []
    for i in range(13):
        u_df_data.append({"name": day_drivers[i], "region": regions[i], "shift": "주간 (08:00~17:30)"})
        u_df_data.append({"name": night_drivers[i], "region": regions[i], "shift": "야간 (18:00~03:00)"})
    u_df = pd.DataFrame(u_df_data)
    
    # 4. 15일치 데이터 펌핑
    KST = timezone(timedelta(hours=9))
    base_date = datetime(2026, 7, 6, tzinfo=KST)
    
    df_data = []       # 탑승(콜) 기록 - GPS 포함!
    df_drive_data = [] # 출퇴근 운행 기록
    
    # 초기 누적 주행거리 랜덤 설정
    km_tracker = {car: random.randint(10000, 50000) for car in m_cars}
    
    for day_offset in range(15): 
        current_date = base_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        
        for i, car in enumerate(m_cars):
            region = regions[i]
            b_lat, b_lon = base_coords[region]
            
            # ==============================
            # ☀️ 주간조 운행
            # ==============================
            driver_d = day_drivers[i]
            start_time_d = current_date.replace(hour=8, minute=random.randint(0, 15))
            start_km_d = km_tracker[car]
            
            df_drive_data.append({
                "id": f"start_{date_str}_D_{car}", "유형": "출발", "차량번호": car, 
                "Safe_Guard": driver_d, "출발자": driver_d, "종료자": "",
                "출발_장소": f"{region} 차고지", "출발_km": start_km_d, 
                "출발_배터리_차량": random.randint(90, 100), "날짜": date_str, "timestamp": start_time_d.isoformat()
            })
            
            # 주간 콜 생성 (6~12건) 및 GPS 난수 생성
            num_rides_d = random.randint(6, 12)
            ride_start = start_time_d + timedelta(minutes=random.randint(10, 30))
            for _ in range(num_rides_d):
                ride_end = ride_start + timedelta(minutes=random.randint(10, 30))
                # 중심 좌표 반경 내 랜덤 GPS 위치 생성
                r_lat = b_lat + random.uniform(-0.03, 0.03)
                r_lon = b_lon + random.uniform(-0.03, 0.03)
                
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver_d,
                    "callCount": random.choices([1, 2], weights=[80, 20])[0],
                    "passengers": random.randint(1, 4), "status": "완료",
                    "latitude": r_lat, "longitude": r_lon # 📍 맵 생성을 위한 GPS 위도/경도 추가
                })
                ride_start = ride_end + timedelta(minutes=random.randint(5, 15))
            
            end_time_d = current_date.replace(hour=17, minute=random.randint(15, 45))
            drive_dist_d = random.randint(60, 120)
            end_km_d = start_km_d + drive_dist_d
            km_tracker[car] = end_km_d
            
            df_drive_data.append({
                "id": f"end_{date_str}_D_{car}", "유형": "종료", "차량번호": car, 
                "Safe_Guard": driver_d, "출발자": "", "종료자": driver_d, 
                "종료_장소": f"{region} 차고지", "종료_km": end_km_d, "총주행거리(km)": drive_dist_d, 
                "종료_배터리_차량": random.randint(20, 50), "날짜": date_str, 
                "timestamp": end_time_d.isoformat(), "특이사항": random.choice(["이상 없음", "이상 없음", "세차 요망"])
            })

            # ==============================
            # 🌙 야간조 운행
            # ==============================
            driver_n = night_drivers[i]
            start_time_n = current_date.replace(hour=18, minute=random.randint(0, 15))
            start_km_n = km_tracker[car]
            
            df_drive_data.append({
                "id": f"start_{date_str}_N_{car}", "유형": "출발", "차량번호": car, 
                "Safe_Guard": driver_n, "출발자": driver_n, "종료자": "",
                "출발_장소": f"{region} 교대거점", "출발_km": start_km_n, 
                "출발_배터리_차량": random.randint(80, 100), "날짜": date_str, "timestamp": start_time_n.isoformat()
            })
            
            # 야간 콜 생성 (5~15건)
            num_rides_n = random.randint(5, 15)
            ride_start = start_time_n + timedelta(minutes=random.randint(10, 30))
            for _ in range(num_rides_n):
                ride_end = ride_start + timedelta(minutes=random.randint(15, 45))
                r_lat = b_lat + random.uniform(-0.03, 0.03)
                r_lon = b_lon + random.uniform(-0.03, 0.03)
                
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver_n,
                    "callCount": random.choices([1, 2], weights=[70, 30])[0],
                    "passengers": random.randint(1, 3), "status": "완료",
                    "latitude": r_lat, "longitude": r_lon # 📍 맵 생성을 위한 GPS 위도/경도 추가
                })
                ride_start = ride_end + timedelta(minutes=random.randint(10, 25))
            
            end_time_n = (current_date + timedelta(days=1)).replace(hour=3, minute=random.randint(0, 30))
            drive_dist_n = random.randint(80, 150)
            end_km_n = start_km_n + drive_dist_n
            km_tracker[car] = end_km_n
            
            df_drive_data.append({
                "id": f"end_{date_str}_N_{car}", "유형": "종료", "차량번호": car, 
                "Safe_Guard": driver_n, "출발자": "", "종료자": driver_n, 
                "종료_장소": f"{region} 차고지", "종료_km": end_km_n, "총주행거리(km)": drive_dist_n, 
                "종료_배터리_차량": random.randint(10, 40), "날짜": end_time_n.strftime("%Y-%m-%d"), 
                "timestamp": end_time_n.isoformat(), "특이사항": random.choice(["이상 없음", "이상 없음", "취객 탑승"])
            })

    return {
        'm_cars': m_cars,
        'm_drivers': m_drivers,
        'u_df': u_df,
        'df': pd.DataFrame(df_data),
        'df_drive': pd.DataFrame(df_drive_data),
        'sched_df': pd.DataFrame([])
    }
