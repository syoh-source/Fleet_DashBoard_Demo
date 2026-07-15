import pandas as pd
import random
from datetime import datetime, timedelta, timezone

def get_demo_data():
    m_cars = [f"E100#{i:02d}" for i in range(1, 14)] # 13대
    
    day_drivers = ["김민준", "이서준", "박도윤", "최시우", "정지호", "강건우", "조은우", "윤선우", "장서진", "임연우", "한유준", "오하준", "서도현"]
    night_drivers = ["김서연", "이서윤", "박지우", "최지민", "정다은", "강하은", "조하윤", "윤시아", "장지율", "임서현", "한아린", "오채원", "서소율"]
    m_drivers = day_drivers + night_drivers
    
    regions = ["상암"]*5 + ["강남"]*4 + ["안양"]*4
    
    # 📍 지역별 타이트한 위경도 범위 (한강 진입 원천 차단)
    bbox = {
        "상암": (37.570, 37.585, 126.875, 126.900),
        "강남": (37.485, 37.515, 127.020, 127.060), # 테헤란로 남쪽 기준 제한
        "안양": (37.380, 37.410, 126.910, 126.950)
    }
    
    u_df_data = []
    for i in range(13):
        u_df_data.append({"name": day_drivers[i], "region": regions[i], "shift": "주간 (08:00~17:30)"})
        u_df_data.append({"name": night_drivers[i], "region": regions[i], "shift": "야간 (18:00~03:00)"})
    u_df = pd.DataFrame(u_df_data)
    
    KST = timezone(timedelta(hours=9))
    base_date = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=15)
    
    df_data = []
    df_drive_data = []
    km_tracker = {car: random.randint(10000, 50000) for car in m_cars}
    
    for day_offset in range(16): 
        current_date = base_date + timedelta(days=day_offset)
        date_str = current_date.strftime("%Y-%m-%d")
        
        for i, car in enumerate(m_cars):
            region = regions[i]
            min_lat, max_lat, min_lon, max_lon = bbox[region]
            
            # ==============================
            # ☀️ 주간조
            # ==============================
            driver_d = day_drivers[i]
            start_time_d = current_date.replace(hour=8, minute=random.randint(0, 15))
            start_km_d = km_tracker[car]
            start_ms_d = int(start_time_d.timestamp() * 1000) # ValueError 방지용 ms 숫자
            
            df_drive_data.append({
                "id": f"start_{date_str}_D_{car}", "유형": "출발", "차량번호": car, 
                "Safe_Guard": driver_d, "출발자": driver_d, "종료자": "",
                "출발_장소": f"{region} 차고지", "출발_km": start_km_d, 
                "출발_배터리_차량": random.randint(90, 100), "날짜": date_str, "timestamp": start_ms_d
            })
            
            num_rides_d = random.randint(6, 12)
            ride_start = start_time_d + timedelta(minutes=random.randint(10, 30))
            for _ in range(num_rides_d):
                ride_end = ride_start + timedelta(minutes=random.randint(10, 30))
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver_d,
                    "callCount": random.choices([1, 2], weights=[80, 20])[0],
                    "passengers": random.randint(1, 4), "status": "완료",
                    "latitude": random.uniform(min_lat, max_lat), "longitude": random.uniform(min_lon, max_lon),
                    "revenue": random.randint(3000, 15000), "이슈건수": random.choices([0, 1], weights=[95, 5])[0]
                })
                ride_start = ride_end + timedelta(minutes=random.randint(5, 15))
            
            end_time_d = current_date.replace(hour=17, minute=random.randint(15, 45))
            end_ms_d = int(end_time_d.timestamp() * 1000)
            drive_dist_d = random.randint(60, 120)
            end_km_d = start_km_d + drive_dist_d
            km_tracker[car] = end_km_d
            
            df_drive_data.append({
                "id": f"end_{date_str}_D_{car}", "유형": "종료", "차량번호": car, 
                "Safe_Guard": driver_d, "출발자": "", "종료자": driver_d, 
                "종료_장소": f"{region} 차고지", "종료_km": end_km_d, "총주행거리(km)": drive_dist_d, 
                "종료_배터리_차량": random.randint(20, 50), "날짜": date_str, 
                "timestamp": end_ms_d, "특이사항": random.choice(["이상 없음", "세차 요망", ""])
            })

            # ==============================
            # 🌙 야간조
            # ==============================
            driver_n = night_drivers[i]
            start_time_n = current_date.replace(hour=18, minute=random.randint(0, 15))
            start_km_n = km_tracker[car]
            start_ms_n = int(start_time_n.timestamp() * 1000)
            
            df_drive_data.append({
                "id": f"start_{date_str}_N_{car}", "유형": "출발", "차량번호": car, 
                "Safe_Guard": driver_n, "출발자": driver_n, "종료자": "",
                "출발_장소": f"{region} 교대거점", "출발_km": start_km_n, 
                "출발_배터리_차량": random.randint(80, 100), "날짜": date_str, "timestamp": start_ms_n
            })
            
            num_rides_n = random.randint(5, 15)
            ride_start = start_time_n + timedelta(minutes=random.randint(10, 30))
            for _ in range(num_rides_n):
                ride_end = ride_start + timedelta(minutes=random.randint(15, 45))
                df_data.append({
                    "timestamp": ride_start.isoformat(),
                    "ride_start_time": int(ride_start.timestamp() * 1000),
                    "ride_end_time": int(ride_end.timestamp() * 1000),
                    "carNumber": car, "driverName": driver_n,
                    "callCount": random.choices([1, 2], weights=[70, 30])[0],
                    "passengers": random.randint(1, 3), "status": "완료",
                    "latitude": random.uniform(min_lat, max_lat), "longitude": random.uniform(min_lon, max_lon),
                    "revenue": random.randint(4000, 20000), "이슈건수": random.choices([0, 1], weights=[90, 10])[0]
                })
                ride_start = ride_end + timedelta(minutes=random.randint(10, 25))
            
            end_time_n = (current_date + timedelta(days=1)).replace(hour=3, minute=random.randint(0, 30))
            end_ms_n = int(end_time_n.timestamp() * 1000)
            drive_dist_n = random.randint(80, 150)
            end_km_n = start_km_n + drive_dist_n
            km_tracker[car] = end_km_n
            end_date_str = end_time_n.strftime("%Y-%m-%d")
            
            df_drive_data.append({
                "id": f"end_{date_str}_N_{car}", "유형": "종료", "차량번호": car, 
                "Safe_Guard": driver_n, "출발자": "", "종료자": driver_n, 
                "종료_장소": f"{region} 차고지", "종료_km": end_km_n, "총주행거리(km)": drive_dist_n, 
                "종료_배터리_차량": random.randint(10, 40), "날짜": end_date_str, 
                "timestamp": end_ms_n, "특이사항": random.choice(["이상 없음", "취객 탑승", ""])
            })

    return {
        'm_cars': m_cars,
        'm_drivers': m_drivers,
        'u_df': u_df,
        'df': pd.DataFrame(df_data),
        'df_drive': pd.DataFrame(df_drive_data),
        'sched_df': pd.DataFrame([])
    }
