import streamlit as st
import pandas as pd
import datetime
import urllib.parse
import os
import time
import requests
import numpy as np
import ast
import json
from chart_utils import *
import summary_trend, summary_time_stats, summary_data_table, summary_geo_analysis

CHUN_ANG_SERVICE_KEY = "wjBTMKih4/tIu0puLg/04/Sw7VSQsJbdmZgrXjwUtpJ44YrEEtXWXxjPCyla576KMKCkRLI5gtgFOIVcUlMzQg=="

def fetch_weather_block(r_name, nx, ny):
    try:
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        s_time = now - datetime.timedelta(hours=1) if now.minute < 40 else now
        b_date = s_time.strftime("%Y%m%d")
        b_time = s_time.strftime("%H00")
        
        ncst = requests.get("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst", 
                            params={"serviceKey": CHUN_ANG_SERVICE_KEY, "pageNo": "1", "numOfRows": "30", "dataType": "JSON", "base_date": b_date, "base_time": b_time, "nx": str(nx), "ny": str(ny)}, timeout=3)
        
        tmp, wnd, rn, pty = 0.0, 0.0, 0.0, 0
        if ncst.status_code == 200 and ncst.text.strip().startswith('{'):
            items = ncst.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            for it in items:
                v = float(it['obsrValue'])
                if it['category'] == "T1H": tmp = v
                elif it['category'] == "WSD": wnd = v
                elif it['category'] == "RN1": rn = v
                elif it['category'] == "PTY": pty = int(v)
        wnd_k = round(wnd * 3.6, 1)

        vh = now.hour
        if vh < 2 or (vh == 2 and now.minute < 15):
            vd = now - datetime.timedelta(days=1)
            vb = "2300"
        elif vh < 5 or (vh == 5 and now.minute < 15): vb = "0200"; vd = now
        elif vh < 8 or (vh == 8 and now.minute < 15): vb = "0500"; vd = now
        elif vh < 11 or (vh == 11 and now.minute < 15): vb = "0800"; vd = now
        elif vh < 14 or (vh == 14 and now.minute < 15): vb = "1100"; vd = now
        elif vh < 17 or (vh == 17 and now.minute < 15): vb = "1400"; vd = now
        elif vh < 20 or (vh == 20 and now.minute < 15): vb = "1700"; vd = now
        elif vh < 23 or (vh == 23 and now.minute < 15): vb = "2000"; vd = now
        else: vb = "2300"; vd = now
        
        v_date = vd.strftime("%Y%m%d")
        fcst = requests.get("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst", 
                            params={"serviceKey": CHUN_ANG_SERVICE_KEY, "pageNo": "1", "numOfRows": "500", "dataType": "JSON", "base_date": v_date, "base_time": vb, "nx": str(nx), "ny": str(ny)}, timeout=3)
        
        forecasts = {}
        d_rn = 0.0
        t_str = now.strftime("%Y%m%d")
        sky = 1
        
        if fcst.status_code == 200 and fcst.text.strip().startswith('{'):
            f_items = fcst.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            for it in f_items:
                fd = it['fcstDate']
                ft = it['fcstTime']
                key = fd + ft
                if key not in forecasts: forecasts[key] = {}
                forecasts[key][it['category']] = it['fcstValue']
                
                if fd == t_str and it['category'] == "PCP":
                    vs = it['fcstValue']
                    if "강수없음" not in vs and "-" not in vs:
                        try: d_rn += float(vs.replace("mm", "").strip())
                        except: pass
                        
        c_key = t_str + now.strftime("%H00")
        if c_key in forecasts:
            sky = int(forecasts[c_key].get("SKY", 1))

        if pty in [1, 4, 5]: ic, dc, bg, tx, mg = "🌧️", "비", "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)", "#ffffff", "안전 거리 확보!"
        elif pty in [2, 3, 6, 7]: ic, dc, bg, tx, mg = "❄️", "눈/빙판", "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)", "#1e293b", "서행 운전 필수!"
        else:
            if sky == 1: ic, dc, bg, tx, mg = "☀️", "맑음", "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)", "#ffffff", "쾌적한 운행 날씨!"
            elif sky == 3: ic, dc, bg, tx, mg = "⛅", "구름 많음", "linear-gradient(135deg, #64748b 0%, #475569 100%)", "#ffffff", "운행하기 좋습니다."
            else: ic, dc, bg, tx, mg = "🌫️", "흐림", "linear-gradient(135deg, #94a3b8 0%, #64748b 100%)", "#ffffff", "시야 확보 주의!"

        h_html = "<style>.weather-scroll::-webkit-scrollbar{height:6px;} .weather-scroll::-webkit-scrollbar-track{background:rgba(255,255,255,0.1);border-radius:10px;} .weather-scroll::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.3);border-radius:10px;}</style>"
        h_html += "<div class='weather-scroll' style='display: flex; gap: 8px; overflow-x: auto; margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px; padding-bottom: 8px;'>"
        
        for i in range(1, 25):
            f_dt = now + datetime.timedelta(hours=i)
            key = f_dt.strftime("%Y%m%d%H00")
            f_h = f_dt.strftime("%H시")
            
            if key in forecasts:
                fdata = forecasts[key]
                ftm = fdata.get('TMP', tmp)
                fsk = int(fdata.get('SKY', 1))
                fpt = int(fdata.get('PTY', 0))
                fpo = fdata.get('POP', 0)
            else:
                ftm, fsk, fpt, fpo = "-", 1, 0, "-"
            
            fic = "🌧️" if fpt in [1, 4] else "❄️" if fpt in [2, 3] else "☀️" if fsk == 1 else "⛅" if fsk == 3 else "🌫️"
            tc = tx if tx == "#ffffff" else "#3b82f6"
            
            h_html += f"<div style='text-align: center; min-width: 65px; background: rgba(255,255,255,0.1); padding: 8px; border-radius: 12px;'><div style='font-size: 11px; color: {tx}; opacity:0.8;'>{f_h}</div><div style='font-size: 20px; margin: 4px 0;'>{fic}</div><div style='font-size: 13px; font-weight: 800; color: {tx};'>{ftm}℃</div><div style='font-size: 11px; color: {tc}; font-weight: 600; margin-top: 2px;'>💧{fpo}%</div></div>"
        h_html += "</div>"

        html = f"<div style='flex: 1; min-width: 320px; background: {bg}; padding: 24px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); color: {tx}; font-family: \"Pretendard\", sans-serif;'><div style='font-size: 15px; font-weight: 800; margin-bottom: 8px; opacity: 0.9;'>📍 {r_name}</div><div style='display: flex; align-items: center; justify-content: space-between;'><div style='display: flex; align-items: center; gap: 10px;'><div style='font-size: 40px;'>{ic}</div><div style='font-size: 32px; font-weight: 800; letter-spacing: -1px;'>{tmp}<span style='font-size: 18px; opacity: 0.7;'>℃</span></div></div><div style='text-align: right;'><div style='font-size: 14px; font-weight: 700;'>{dc}</div><div style='font-size: 12px; opacity: 0.8;'>풍속: {wnd_k}km/h</div></div></div><div style='background: rgba(255,255,255,0.15); padding: 12px 16px; border-radius: 12px; font-size: 12px; line-height: 1.6; font-weight: 600; margin-top: 15px;'><div style='display:flex; justify-content:space-between;'><span>💧 시간당 강수량:</span><span>{rn} mm</span></div><div style='display:flex; justify-content:space-between;'><span>☂️ 오늘 총 예상 강수:</span><span>{round(d_rn, 1)} mm</span></div><div style='display:flex; justify-content:space-between; color:#fbbf24;'><span>🚨 특이사항:</span><span>{mg}</span></div></div>{h_html}</div>"
        return html.replace('\n', '')
    except Exception as e:
        return f"<div style='flex: 1; min-width: 320px; padding: 20px; background: #fee2e2; border-radius: 20px; color: #ef4444; font-weight: 600;'>🚨 {r_name} 기상 응답 지연</div>"

@st.cache_data(ttl=1800, show_spinner="weather UI 로딩 중...")
def get_toss_style_weather(target_region):
    regions = {"상암": (59, 127), "강남": (61, 125), "안양": (58, 121)}
    targets = regions.items() if target_region == "전체" else [(target_region, regions.get(target_region, (59, 127)))]
    
    c_file = f"json_DB/weather_cache_{target_region}.txt"
    if not os.path.exists("json_DB"): os.makedirs("json_DB")
    
    if os.path.exists(c_file) and time.time() - os.path.getmtime(c_file) < 600:
        with open(c_file, "r", encoding="utf-8") as f: 
            return f.read()
        
    html = "<div style='display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px;'>"
    for r_name, (nx, ny) in targets:
        html += fetch_weather_block(r_name, nx, ny)
    html += "</div>"
    
    try:
        with open(c_file, "w", encoding="utf-8") as f: 
            f.write(html)
    except: pass
    return html

def draw_summary_tab(clean_df, df_drive_raw):
    mbl = st.session_state.get('is_mobile', False)
    
    # ======== 1. 날씨 위젯 표출 ========
    view_region = st.session_state.get("view_region", "전체")
    weather_html = get_toss_style_weather(view_region)
    st.markdown(weather_html, unsafe_allow_html=True)
    
    # ======== 2. KPI 카드 표출 ========
    if not clean_df.empty:
        t_calls = int(clean_df['callCount'].sum())
        t_pass = int(clean_df['passengers'].sum())
        t_rev = int(clean_df.get('revenue', pd.Series([0])).sum())
        t_cars = int(clean_df['carNumber'].nunique())
        t_issues = int(clean_df.get('이슈건수', pd.Series([0])).sum())
    else:
        t_calls = t_pass = t_rev = t_cars = t_issues = 0

    st.markdown("### 📈 전체 운영 성과 요약")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("총 호출 수", f"{t_calls:,} 건")
    c2.metric("총 탑승객 수", f"{t_pass:,} 명")
    c3.metric("예상 수입금", f"{t_rev:,} 원")
    c4.metric("운영 차량", f"{t_cars} 대")
    c5.metric("이슈 발생", f"{t_issues} 건")
    st.divider()
    
    if "init_call_id_done" not in st.session_state:
        r_id = st.query_params.get("call_id", st.session_state.get("saved_call_id", None))
        if r_id: st.session_state["saved_call_id"] = urllib.parse.unquote_plus(r_id).replace("+", " ")
        st.session_state["init_call_id_done"] = True
    if st.session_state.get("summary_view_state") not in ["🗺️ 위치 및 경로", None]:
        if "call_id" in st.query_params: del st.query_params["call_id"]
        if "saved_call_id" in st.session_state: del st.session_state["saved_call_id"]

    drv = df_drive_raw.copy()
    smg = pd.DataFrame()
    dmg = pd.DataFrame()
    
    if not drv.empty:
        drv['총주행거리(km)'] = pd.to_numeric(drv.get('총주행거리(km)', 0), errors='coerce').fillna(0)
        drv['특이사항'] = drv.get('특이사항', '').astype(str).replace(['nan', 'None', 'NaN'], '').str.strip()
        drv['유형_clean'] = drv['유형'].astype(str).str.replace(' ', '').str.strip() if '유형' in drv.columns else '알수없음'
        if '차량번호' in drv.columns: drv['차량번호'] = drv['차량번호'].astype(str).str.replace(' ', '').str.strip()
        
        def p_ts(v):
            if pd.isna(v) or v == "": return pd.NaT
            try: return pd.to_datetime(float(v), unit='ms', utc=True) if isinstance(v, (int, float)) or (isinstance(v, str) and str(v).replace('.', '').isdigit()) else pd.to_datetime(str(v), errors='coerce', utc=True)
            except: return pd.NaT
            
        drv['dt_obj'] = drv['timestamp'].apply(p_ts) if 'timestamp' in drv.columns else drv['날짜'].apply(p_ts)
        drv['dt_obj'] = pd.to_datetime(drv['dt_obj'], utc=True).dt.tz_convert('Asia/Seoul')
        drv = drv.sort_values(['차량번호', 'dt_obj']).reset_index(drop=True)
        drv['is_start'] = drv['유형_clean'].isin(['출발', '시작', '출근'])
        drv['shift_id'] = drv.groupby('차량번호')['is_start'].cumsum()
        s_map = drv[drv['is_start']].groupby(['차량번호', 'shift_id'])['dt_obj'].first().to_dict()
        drv['shift_start_dt'] = pd.to_datetime(drv.set_index(['차량번호', 'shift_id']).index.map(s_map).values)
        drv['shift_start_dt'] = drv['shift_start_dt'].fillna(drv['dt_obj'])
        drv['shift_date'] = drv['shift_start_dt'].apply(lambda d: (d - datetime.timedelta(days=1)).strftime('%Y-%m-%d') if pd.notna(d) and d.hour < 6 else (d.strftime('%Y-%m-%d') if pd.notna(d) else None))
        
        dfs = drv[drv['is_start']].copy().sort_values('dt_obj').rename(columns={'Safe_Guard': '출발자', 'timestamp': '출발_시간'})
        dfs = dfs[[c for c in ['shift_date', '차량번호', 'shift_id', '출발자', '출발_시간', '출발_장소', '출발_km', '출발_배터리_차량', '출발_배터리_폰', '출발_배터리_앞탭', '출발_배터리_뒤탭'] if c in dfs.columns]].drop_duplicates(subset=['shift_date', '차량번호', 'shift_id'], keep='first')
        dfe = drv[drv['유형_clean'].isin(['종료', '복귀', '도착', '퇴근', '마감'])].copy().sort_values('dt_obj').rename(columns={'Safe_Guard': '종료자', 'timestamp': '종료_시간'})
        dfe = dfe[[c for c in ['shift_date', '차량번호', 'shift_id', '종료자', '종료_시간', '종료_장소', '종료_km', '종료_배터리_차량', '종료_배터리_폰', '종료_배터리_앞탭', '종료_배터리_뒤탭', '총주행거리(km)', '특이사항'] if c in dfe.columns]].drop_duplicates(subset=['shift_date', '차량번호', 'shift_id'], keep='last')
        
        smg = pd.merge(dfs, dfe, on=['shift_date', '차량번호', 'shift_id'], how='outer')
        
        # 에러 방지용 누락 컬럼 강제 생성
        required_cols = [
            '출발자', '종료자', '출발_시간', '종료_시간', '출발_장소', '종료_장소', 
            '출발_km', '종료_km', '출발_배터리_차량', '출발_배터리_폰', '출발_배터리_앞탭', 
            '출발_배터리_뒤탭', '종료_배터리_차량', '종료_배터리_폰', '종료_배터리_앞탭', 
            '종료_배터리_뒤탭', '특이사항'
        ]
        for col in required_cols:
            if col not in smg.columns:
                smg[col] = pd.NA

        def g_hm(v):
            if pd.isna(v) or v in ['-', '']: return ''
            try: return datetime.datetime.fromtimestamp(float(v)/1000).strftime('%H:%M') if isinstance(v, (int, float)) or (isinstance(v, str) and str(v).replace('.', '').isdigit()) else pd.to_datetime(str(v), errors='coerce').strftime('%H:%M')
            except: return ''
            
        smg['출발_hm'] = smg['출발_시간'].apply(g_hm)
        smg['종료_hm'] = smg['종료_시간'].apply(g_hm)
        smg['shift_count'] = smg.groupby(['shift_date', '차량번호'])['shift_id'].transform('nunique')
        smg['calendar_text'] = smg.apply(lambda r: f"{r['차량번호']} ({r['출발_hm']}~{r['종료_hm']})" if r['shift_count'] > 1 and r['출발_hm'] and r['종료_hm'] else str(r['차량번호']), axis=1)
        
        dmg = smg.sort_values('shift_id').groupby(['shift_date', '차량번호']).agg(
            출발자=('출발자', lambda x: ', '.join(sorted(set([str(v).strip() for v in x if pd.notna(v) and str(v).strip() not in ['', '-', 'nan', 'None']]))) or '-'),
            종료자=('종료자', lambda x: ', '.join(sorted(set([str(v).strip() for v in x if pd.notna(v) and str(v).strip() not in ['', '-', 'nan', 'None']]))) or '-'),
            출발_시간=('출발_시간', 'first'), 종료_시간=('종료_시간', 'last'), 출발_장소=('출발_장소', 'first'), 종료_장소=('종료_장소', 'last'),
            출발_km=('출발_km', 'first'), 종료_km=('종료_km', 'last'), 출발_배터리_차량=('출발_배터리_차량', 'first'), 출발_배터리_폰=('출발_배터리_폰', 'first'),
            출발_배터리_앞탭=('출발_배터리_앞탭', 'first'), 출발_배터리_뒤탭=('출발_배터리_뒤탭', 'first'), 종료_배터리_차량=('종료_배터리_차량', 'last'),
            종료_배터리_폰=('종료_배터리_폰', 'last'), 종료_배터리_앞탭=('종료_배터리_앞탭', 'last'), 종료_배터리_뒤탭=('종료_배터리_뒤탭', 'last'),
            특이사항=('특이사항', lambda x: ' / '.join([str(v).strip() for v in x if pd.notna(v) and str(v).strip() not in ['', '-', 'nan', 'None']]) or '-')
        ).reset_index()
        
        for c in ['출발_km', '종료_km', '총주행거리(km)']:
            if c not in dmg.columns: dmg[c] = 0
        if '특이사항' not in dmg.columns: dmg['특이사항'] = ''
        
        dmg['s_k'] = pd.to_numeric(dmg['출발_km'], errors='coerce').fillna(0)
        dmg['e_k'] = pd.to_numeric(dmg['종료_km'], errors='coerce').fillna(0)
        msk = (dmg['e_k'] > 0) & (dmg['s_k'] > 0) & (dmg['e_k'] >= dmg['s_k'])
        dmg.loc[msk, '총주행거리(km)'] = dmg.loc[msk, 'e_k'] - dmg.loc[msk, 's_k']
        dmg['총주행거리(km)'] = dmg['총주행거리(km)'].fillna(0)
        dmg['특이사항'] = dmg['특이사항'].fillna('')

        def calc_duration(r):
            if pd.isna(r['출발_시간']) or pd.isna(r['종료_시간']):
                return ""
            try:
                # 숫자형 타임스탬프 처리 지원을 위해 to_datetime에 unit 설정 유연화 필요 없음 (g_hm처럼 텍스트로 안넘어올수있으므로 안전하게)
                if isinstance(r['종료_시간'], (int, float)) or (isinstance(r['종료_시간'], str) and r['종료_시간'].isdigit()):
                     t_end = pd.to_datetime(float(r['종료_시간']), unit='ms', utc=True)
                else:
                     t_end = pd.to_datetime(r['종료_시간'], utc=True)
                     
                if isinstance(r['출발_시간'], (int, float)) or (isinstance(r['출발_시간'], str) and r['출발_시간'].isdigit()):
                     t_start = pd.to_datetime(float(r['출발_시간']), unit='ms', utc=True)
                else:
                     t_start = pd.to_datetime(r['출발_시간'], utc=True)
                     
                td = t_end - t_start
                total_seconds = int(td.total_seconds())
                
                if total_seconds < 0: 
                    return ""
                    
                hours, remainder = divmod(total_seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                return f"{hours}시간 {minutes}분"
            except:
                return ""
                
        dmg['운행시간'] = dmg.apply(calc_duration, axis=1)

    # ======== 3. 달력 주야간 분리 및 정렬 ========
    if not clean_df.empty:
        cdf = clean_df.copy()
        def safe_dt_parse(v):
            if pd.isna(v) or str(v).strip() == '': return pd.NaT
            try: return pd.to_datetime(float(v), unit='ms', utc=True).tz_convert('Asia/Seoul') if isinstance(v, (int, float)) or (isinstance(v, str) and str(v).replace('.', '').isdigit()) else (pd.to_datetime(str(v), errors='coerce').tz_convert('Asia/Seoul') if pd.to_datetime(str(v), errors='coerce').tzinfo else pd.to_datetime(str(v), errors='coerce').tz_localize('Asia/Seoul'))
            except: return pd.NaT
            
        t_col = cdf.get('dt_obj', cdf.get('timestamp', cdf.get('ride_start_time', pd.Series(index=cdf.index, dtype=object))))
        cdf['dt_obj'] = t_col.apply(safe_dt_parse)
        cdf['carNumber'] = cdf.get('carNumber', cdf.get('차량번호', '알수없음')).astype(str).str.replace(' ', '').str.strip()
        cdf['carNumber'] = cdf['carNumber'].replace(['nan', 'None', ''], '알수없음')
        cdf['driverName'] = cdf.get('driverName', cdf.get('운전자', '알수없음')).fillna('알수없음')
        cdf['driverName'] = cdf['driverName'].replace(['nan', 'None', ''], '알수없음')
        
        # 달력 주/야간 그룹핑 생성
        cdf['hour'] = cdf['dt_obj'].dt.hour
        cdf['is_night'] = cdf['hour'].apply(lambda h: True if pd.notna(h) and (h >= 18 or h < 6) else False)
        cdf['shift_icon'] = cdf['is_night'].map({False: "☀️ 주간", True: "🌙 야간"})
        
        # 캘린더에 표시될 텍스트 (주간/야간 태그 + 차량번호)
        cdf['calendar_text'] = cdf['shift_icon'] + " | " + cdf['carNumber']
        
        # 주간이 위로, 야간이 아래로 오도록 + 그 안에서 차량번호 순으로 정렬
        cdf = cdf.sort_values(by=['is_night', 'carNumber'], ascending=[True, True])
        
        cdf['callCount'] = pd.to_numeric(cdf.get('callCount', 0), errors='coerce').fillna(0)
        cdf['passengers'] = pd.to_numeric(cdf.get('passengers', 0), errors='coerce').fillna(0)
        cdf['shift_date'] = cdf['dt_obj'].apply(lambda d: (d - datetime.timedelta(days=1)).date() if pd.notna(d) and d.hour < 6 else (d.date() if pd.notna(d) else None))
        
        def r_js(v):
            if isinstance(v, (dict, list)): return v
            if isinstance(v, str):
                v = v.strip()
                if not v: return {}
                try: return ast.literal_eval(v)
                except:
                    try: return json.loads(v)
                    except: return {}
            return {}
            
        if 'report_memos' in cdf.columns: cdf['report_memos'] = cdf['report_memos'].apply(r_js)
        if 'issue_pings' in cdf.columns: cdf['issue_pings'] = cdf['issue_pings'].apply(r_js)
        
        cdf['chart_category'] = cdf.apply(classify_data, axis=1)
        cdf['time_bracket'] = cdf['hour'].apply(get_time_bracket)
        cdf['is_manual'] = cdf['chart_category'].apply(lambda x: '📦 일괄 입력' if '일괄' in x else '🚕 정상 운행')
        cdf['revenue'] = cdf.apply(calc_revenue, axis=1)
        cdf['이슈건수'] = cdf.apply(lambda r: int(r.get('report_memos', {}).get('ADMIN_ISSUE_COUNT', r.get('이슈건수', 0)) if isinstance(r.get('report_memos'), dict) else r.get('이슈건수', 0)), axis=1)
        if 'remark' not in cdf.columns: cdf['remark'] = ''
        
        def x_m(r):
            ms = r.get('report_memos', {})
            if isinstance(ms, dict):
                if 'ADMIN_EDIT' in ms and str(ms['ADMIN_EDIT']).strip(): return f"{str(ms['ADMIN_EDIT']).strip()} (admin)"
                ap = [str(v) for k, v in ms.items() if not str(k).startswith('ADMIN_') and str(v).strip()]
                if ap: return " / ".join(ap) + " (app)"
            elif isinstance(ms, list) and ms:
                ap = [str(x) for x in ms if str(x).strip()]
                if ap: return " / 대여 (app)"
            return ""
            
        cdf['통합_이슈상세'] = cdf.apply(x_m, axis=1)
        
        clean_df = cdf
    else:
        clean_df = pd.DataFrame(columns=['timestamp_str', 'date_str', 'dt_obj', 'carNumber', 'driverName', 'passengers', 'callCount', 'remark', 'status', 'calendar_text', 'chart_category', 'hour', 'time_bracket', 'is_manual', 'revenue', '이슈건수', '통합_이슈상세', 'shift_date'])

    draw_html_calendar(clean_df, 'calendar_text', '운영 현황 (달력)')
    st.divider()
    st.markdown("### 📊 통합 운영 상세 분석")
    if "summary_view_state" not in st.session_state: 
        st.session_state["summary_view_state"] = "🗺️ 위치 및 경로" if st.session_state.get("saved_call_id") else "📈 시계열 트렌드"
        
    ops = ["📈 시계열 트렌드", "⏰ 시간대별 탑승객 통계", "📋 운행일지 및 탑승정보", "🗺️ 위치 및 경로"]
    idx = ops.index(st.session_state["summary_view_state"]) if st.session_state["summary_view_state"] in ops else 0
    
    st.radio("보기 옵션 선택", ops, index=idx, horizontal=not mbl, label_visibility="collapsed", key="summary_view_widget", on_change=lambda: st.session_state.update({"summary_view_state": st.session_state.summary_view_widget}))
    st.write("")

    if st.session_state["summary_view_state"] == "📈 시계열 트렌드": summary_trend.draw_trend_view(clean_df, dmg, mbl)
    elif st.session_state["summary_view_state"] == "⏰ 시간대별 탑승객 통계": summary_time_stats.draw_time_stats_view(clean_df, mbl)
    elif st.session_state["summary_view_state"] == "📋 운행일지 및 탑승정보": summary_data_table.draw_data_table_view(clean_df, dmg, mbl)
    elif st.session_state["summary_view_state"] == "🗺️ 위치 및 경로": summary_geo_analysis.draw_geo_view(clean_df, mbl)
