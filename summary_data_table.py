import streamlit as st; import pandas as pd; import datetime; import firebase_manager as fm
def calc_travel_time(s_ms,e_ms):
    try: s=int(float(s_ms)); e=int(float(e_ms)); d=(e-s)//1000; return '-' if d<0 else f"{d//60}분 {d%60}초"
    except: return '-'
def get_time_str(ms,fmt='datetime'):
    if pd.isna(ms) or str(ms).strip()=='': return '-'
    try: dt=pd.to_datetime(int(float(ms)),unit='ms',utc=True).tz_convert('Asia/Seoul'); return dt.strftime('%H:%M:%S') if fmt=='time' else (dt.strftime('%Y-%m-%d') if fmt=='date' else dt.strftime('%Y-%m-%d %H:%M:%S'))
    except: return str(ms)
def get_valid_str(row,keys,default='-'):
    for k in keys:
        if (isinstance(row,dict) and k in row) or (hasattr(row,'index') and k in row.index):
            val=row[k]
            if pd.notna(val) and str(val).strip() not in ['','nan','NaN','None']: return str(val).strip()
    return default
def get_sw_info(row,sw_db):
    c_num=get_valid_str(row,['차량번호','carNumber','match_car']); ms=get_valid_str(row,['time','ride_start_time','timestamp']); r_time=pd.Timestamp.min
    try: r_time=pd.to_datetime(int(float(ms)),unit='ms',utc=True).tz_convert('Asia/Seoul').tz_localize(None) if ms!='-' and ms.replace('.','').isdigit() else (pd.to_datetime(get_valid_str(row,['발생시간','운행일자','timestamp_str','dt_obj']),errors='coerce').tz_convert('Asia/Seoul').tz_localize(None) if get_valid_str(row,['발생시간','운행일자','timestamp_str','dt_obj'])!='-' else pd.Timestamp.min)
    except: pass
    app_sv=get_valid_str(row,['SW_Safeview','Safeview','app_Safeview'])
    if app_sv!='-': return {'Safeview':app_sv,'CPU':get_valid_str(row,['SW_CPU','CPU','app_CPU']),'MCU':get_valid_str(row,['SW_MCU','MCU','app_MCU']),'VPU1':get_valid_str(row,['SW_VPU1','VPU1','app_VPU1']),'VPU2':get_valid_str(row,['SW_VPU2','VPU2','app_VPU2']),'VPU3':get_valid_str(row,['SW_VPU3','VPU3','app_VPU3']),'VPU4':get_valid_str(row,['SW_VPU4','VPU4','app_VPU4'])}
    matched={'Safeview':'-','CPU':'-','MCU':'-','VPU1':'-','VPU2':'-','VPU3':'-','VPU4':'-'}
    for sw in sw_db:
        if sw.get('carNumber','')==c_num and r_time>=sw['apply_datetime']: matched=sw
    return matched
def draw_data_table_view(clean_df,df_drive_merged,is_mobile):
    if is_mobile: st.info("📱 모바일 환경에서는 스와이프(밀기)해서 숨겨진 데이터 확인이 가능합니다.")
    if not clean_df.empty: clean_df=clean_df.loc[:, ~clean_df.columns.duplicated()].copy()
    sw_db_list=[]
    try:
        for k,v in fm.load_data('sw_versions').items():
            dt_val=pd.to_datetime(f"{v.get('apply_date','1970-01-01')} {v.get('apply_time','00:00:00')}",errors='coerce'); v['apply_datetime']=dt_val.tz_convert('Asia/Seoul').tz_localize(None) if pd.notna(dt_val) and dt_val.tzinfo else (dt_val if pd.notna(dt_val) else pd.Timestamp.min); sw_db_list.append(v)
        sw_db_list=sorted(sw_db_list,key=lambda x:x['apply_datetime'])
    except: pass
    t_style="<style>.log-table{width:100%;min-width:1200px;border-collapse:collapse;text-align:center;font-size:13px;font-family:Pretendard,sans-serif;white-space:nowrap;}.log-table th,.log-table td{border-bottom:1px solid #e2e8f0;border-right:1px solid #f1f5f9;padding:12px 10px;}.log-table th{background-color:#f8fafc;color:#334155;font-weight:700;position:sticky;top:0;z-index:1;box-shadow:0 1px 0 #e2e8f0;}.log-table tbody tr:hover{background-color:#f1f5f9;transition:background-color 0.2s;}</style>"
    st.markdown("### 📋 현장 탑승 기록 상세")
    if not clean_df.empty:
        raw_disp=clean_df[clean_df.get('status','')!='ISSUE_ONLY'].copy()
        if not raw_disp.empty:
            c1,c2=st.columns([1,1]); s_col=c1.selectbox("정렬 기준 (탑승 기록)",['운행일자','차량번호','운전자'],key='s1'); s_asc=c2.radio("정렬 방식",['내림차순','오름차순'],horizontal=True,key='a1')=='오름차순'; raw_disp=raw_disp.sort_values({'운행일자':'ride_start_time','차량번호':'carNumber','운전자':'driverName'}.get(s_col,raw_disp.columns[0]),ascending=s_asc)
            h1=f"<div style='overflow-x:auto;max-height:500px;border-radius:16px;border:1px solid #e2e8f0;-webkit-overflow-scrolling:touch;'>{t_style}<table class='log-table'><thead><tr><th style='background-color:#e0e7ff'>운행일자</th><th style='background-color:#e0e7ff'>차량번호</th><th style='background-color:#e0e7ff'>운전자</th><th style='background-color:#fce7f3'>승차시간</th><th style='background-color:#fce7f3'>하차시간</th><th style='background-color:#dbeafe'>탑승 위치 (위도, 경도)</th><th style='background-color:#dbeafe'>하차 위치 (위도, 경도)</th><th style='background-color:#fef3c7'>이동시간</th></tr></thead><tbody>"
            for _,r in raw_disp.iterrows():
                r_s=get_valid_str(r,['ride_start_time']); r_e=get_valid_str(r,['ride_end_time']); b_lat=get_valid_str(r,['latitude','board_lat','탑승위도']); b_lon=get_valid_str(r,['longitude','board_lon','탑승경도']); a_lat=get_valid_str(r,['end_latitude','alight_lat','하차위도']); a_lon=get_valid_str(r,['end_longitude','alight_lon','하차경도'])
                h1+=f"<tr><td>{get_time_str(r_s,'date') if r_s!='-' else get_valid_str(r,['dt_obj','운행일자'])}</td><td>{get_valid_str(r,['carNumber','차량번호'])}</td><td>{get_valid_str(r,['driverName','운전자'])}</td><td>{get_time_str(r_s,'time') if r_s!='-' else get_valid_str(r,['board_time','승차시간'])}</td><td>{get_time_str(r_e,'time') if r_e!='-' else get_valid_str(r,['alight_time','하차시간'])}</td><td>{f'{b_lat}, {b_lon}' if b_lat not in ['-','nan','','None'] else '-'}</td><td>{f'{a_lat}, {a_lon}' if a_lat not in ['-','nan','','None'] else '-'}</td><td>{calc_travel_time(r_s,r_e) if r_s!='-' and r_e!='-' else get_valid_str(r,['travel_time','이동시간'])}</td></tr>"
            st.markdown(h1+"</tbody></table></div>",unsafe_allow_html=True)
        else: st.info("💡 기록 없음")
    else: st.info("💡 기록 없음")
    st.divider(); st.markdown("### 🚨 이슈 발굴 기록 상세")
    c_iss=[]
    if not clean_df.empty:
        for _,r in clean_df.iterrows():
            pings=r.get('issue_pings',[]); pings=pings if isinstance(pings,list) else []; memos=r.get('report_memos',{}); memos=memos if isinstance(memos,dict) else {}; p_map={str(p['time']):{'lat':str(p.get('lat',p.get('latitude','-'))),'lon':str(p.get('lng',p.get('longitude','-')))} for p in pings if isinstance(p,dict) and 'time' in p}; a_times=sorted(list(set(list(memos.keys())+list(p_map.keys()))))
            if not a_times and get_valid_str(r,['status'])=='ISSUE_ONLY':
                ms=get_valid_str(r,['ride_start_time','timestamp','time'])
                if ms!='-': a_times.append(ms)
            for ts in a_times:
                m_str=str(memos.get(ts,'')).strip(); m_cat,s_cat,dtl="-","-",m_str
                if m_str.startswith('[') and ']' in m_str:
                    c_idx=m_str.index(']'); dtl=m_str[c_idx+1:].strip() or '-'; cats=m_str[1:c_idx].split('>'); m_cat=cats[0].strip() if cats else "-"; s_cat=cats[1].strip() if len(cats)>1 else "-"
                else: dtl=dtl or '-'
                loc=p_map.get(ts,{}); c_iss.append({'time_ms':ts,'발생시간':get_time_str(ts,'datetime'),'차량번호':get_valid_str(r,['carNumber','차량번호']),'운전자':get_valid_str(r,['driverName','운전자']),'대분류':m_cat,'중분류':s_cat,'내용 상세':dtl,'위도':loc.get('lat',get_valid_str(r,['latitude','lat','위도'])),'경도':loc.get('lon',get_valid_str(r,['longitude','lng','경도','lon'])),'_raw':r.to_dict() if hasattr(r,'to_dict') else r})
    if c_iss:
        i_df=pd.DataFrame(c_iss); c3,c4=st.columns([1,1]); s_c2=c3.selectbox("정렬 기준",['발생시간','차량번호','운전자','대분류'],key='s2'); s_a2=c4.radio("정렬",['내림차순','오름차순'],horizontal=True,key='a2')=='오름차순'; i_df=pd.concat([i_df.drop(columns=['_raw']),pd.DataFrame([get_sw_info(i['_raw'],sw_db_list) for i in c_iss])],axis=1); s_m2={'발생시간':'time_ms','차량번호':'차량번호','운전자':'운전자','대분류':'대분류'}.get(s_c2,'time_ms')
        if s_m2 in i_df.columns: i_df=i_df.sort_values(s_m2,ascending=s_a2)
        h2=f"<div style='overflow-x:auto;max-height:500px;border-radius:16px;border:1px solid #e2e8f0;-webkit-overflow-scrolling:touch;'>{t_style}<table class='log-table'><thead><tr><th>발생시간</th><th>차량번호</th><th>운전자</th><th style='background-color:#fee2e2'>대분류</th><th style='background-color:#fee2e2'>중분류</th><th style='background-color:#fee2e2'>내용 상세</th><th>위도</th><th>경도</th><th style='background-color:#f3e8ff'>Safeview</th><th style='background-color:#f3e8ff'>CPU</th><th style='background-color:#f3e8ff'>MCU</th><th style='background-color:#f3e8ff'>V1</th><th style='background-color:#f3e8ff'>V2</th><th style='background-color:#f3e8ff'>V3</th><th style='background-color:#f3e8ff'>V4</th></tr></thead><tbody>"
        for _,r in i_df.iterrows(): h2+=f"<tr><td>{r.get('발생시간','-')}</td><td>{r.get('차량번호','-')}</td><td>{r.get('운전자','-')}</td><td style='color:#b91c1c;font-weight:bold;'>{r.get('대분류','-')}</td><td>{r.get('중분류','-')}</td><td style='text-align:left;white-space:normal;min-width:200px;'>{r.get('내용 상세','-')}</td><td>{r.get('위도','-')}</td><td>{r.get('경도','-')}</td><td>{r.get('Safeview','-')}</td><td>{r.get('CPU','-')}</td><td>{r.get('MCU','-')}</td><td>{r.get('VPU1','-')}</td><td>{r.get('VPU2','-')}</td><td>{r.get('VPU3','-')}</td><td>{r.get('VPU4','-')}</td></tr>"
        st.markdown(h2+"</tbody></table></div>",unsafe_allow_html=True)
    else: st.info("💡 기록 없음")
    st.divider(); st.markdown("### 🚖 차량 별 운행 일지")
    if not df_drive_merged.empty:
        df_disp=df_drive_merged.copy(); df_disp['차량번호_안전']=df_disp.apply(lambda r: get_valid_str(r,['차량번호','carNumber']).replace(' ',''),axis=1); df_disp['shift_date_str']=df_disp.get('shift_date',df_disp.get('날짜','-'))
        c5,c6=st.columns([1,1]); s_c3=c5.selectbox("정렬 기준",['운행일자','차량번호'],key='s3'); s_a3=c6.radio("정렬",['내림차순','오름차순'],horizontal=True,key='a3')=='오름차순'
        if not clean_df.empty:
            s_cln=clean_df.copy(); s_cln['차량번호_안전']=s_cln.apply(lambda r: str(r.get('carNumber',r.get('차량번호',''))).replace(' ',''),axis=1)
            if 'dt_obj' not in s_cln.columns and 'dt_obj_x' in s_cln.columns: s_cln['dt_obj']=s_cln['dt_obj_x']
            if 'dt_obj' in s_cln.columns: s_cln['shift_date_str']=s_cln['dt_obj'].apply(lambda d: (d-datetime.timedelta(days=1)).strftime('%Y-%m-%d') if pd.notna(d) and d.hour<6 else (d.strftime('%Y-%m-%d') if pd.notna(d) else None))
            else: s_cln['shift_date_str']=None
            s_cln['shift_date_str']=s_cln.apply(lambda r: r.get('shift_date_str') if pd.notna(r.get('shift_date_str')) else get_valid_str(r,['shift_date','날짜','운행일자']),axis=1)
            r_inf=s_cln.groupby(['shift_date_str','차량번호_안전']).agg(운행자=('driverName',lambda x: ', '.join(sorted(set([str(v) for v in x if pd.notna(v) and str(v)!=''])))),일일호출=('callCount','sum'),일일탑승=('passengers','sum')).reset_index()
            df_disp['차량번호_안전']=df_disp.get('차량번호_안전',df_disp.get('차량번호')).astype(str); df_disp['shift_date_str']=df_disp.get('shift_date_str',df_disp.get('shift_date')).astype(str); r_inf['차량번호_안전']=r_inf.get('차량번호_안전').astype(str); r_inf['shift_date_str']=r_inf.get('shift_date_str').astype(str); df_disp=pd.merge(df_disp,r_inf,on=['shift_date_str','차량번호_안전'],how='left')
        else: df_disp['운행자'],df_disp['일일호출'],df_disp['일일탑승']='-','-','-'
        def safe_pt(v): return pd.to_datetime(int(float(v)),unit='ms',utc=True).tz_convert('Asia/Seoul').strftime('%H:%M:%S') if pd.notna(v) and v not in ['-',''] and (isinstance(v,(int,float)) or (isinstance(v,str) and v.replace('.','').isdigit())) else (pd.to_datetime(str(v),errors='coerce').strftime('%H:%M:%S') if pd.notna(v) and v not in ['-',''] else '-')
        df_disp['출발_시간']=df_disp.apply(lambda r: safe_pt(r.get('출발_시간')),axis=1); df_disp['종료_시간']=df_disp.apply(lambda r: safe_pt(r.get('종료_시간')),axis=1); a_sc='shift_date_str' if s_c3=='운행일자' else '차량번호_안전'; df_disp=df_disp.fillna('-').sort_values([a_sc,'차량번호_안전' if a_sc!='차량번호_안전' else 'shift_date_str'],ascending=[s_a3,True]); df_disp['운행일자']=df_disp.get('shift_date_str','-')
        try: df_disp['운행일자']=pd.to_datetime(df_disp['운행일자']).dt.strftime('%m/%d').fillna('-')
        except: pass
        h3=f"<div style='overflow-x:auto;overflow-y:auto;max-height:500px;-webkit-overflow-scrolling:touch;margin-top:15px;border-radius:16px;border:1px solid #e2e8f0;box-shadow:0 4px 20px rgba(0,0,0,0.03);background:white;'>{t_style}<table class='log-table'><thead><tr><th rowspan='2' style='background-color:#e2e8f0;'>운행<br>일자</th><th rowspan='2' style='background-color:#e2e8f0;'>차량<br>번호</th><th colspan='3' style='background-color:#e0e7ff !important;'>담당</th><th colspan='2' style='background-color:#fce7f3 !important;'>탑승 실적</th><th colspan='3' style='background-color:#fef3c7 !important;'>계기판 (km)</th><th colspan='2' style='background-color:#dbeafe !important;'>시간</th><th colspan='2' style='background-color:#dcfce7 !important;'>차량 배터리(%)</th><th colspan='7' style='background-color:#f3e8ff !important;'>S/W 버전</th><th rowspan='2' style='background-color:#e2e8f0;'>특이사항</th></tr><tr><th style='background-color:#eef2ff;'>출발자</th><th style='background-color:#eef2ff;color:#4F46E5;'>운행자</th><th style='background-color:#eef2ff;'>종료자</th><th style='background-color:#fdf2f8;'>호출(건)</th><th style='background-color:#fdf2f8;'>탑승(명)</th><th style='background-color:#fffbeb;'>시작</th><th style='background-color:#fffbeb;'>종료</th><th style='background-color:#fef3c7;'>운행거리</th><th style='background-color:#eff6ff;'>출발</th><th style='background-color:#eff6ff;'>도착</th><th style='background-color:#f0fdf4;'>시작</th><th style='background-color:#f0fdf4;'>종료</th><th style='background-color:#fae8ff;'>SV</th><th style='background-color:#fae8ff;'>CPU</th><th style='background-color:#fae8ff;'>MCU</th><th style='background-color:#fae8ff;'>V1</th><th style='background-color:#fae8ff;'>V2</th><th style='background-color:#fae8ff;'>V3</th><th style='background-color:#fae8ff;'>V4</th></tr></thead><tbody>"
        for _,r in df_disp.iterrows():
            cv=get_valid_str(r,['일일호출']); cv=f"{int(float(cv))}" if cv!='-' else cv; pv=get_valid_str(r,['일일탑승']); pv=f"{int(float(pv))}" if pv!='-' else pv; c_num=get_valid_str(r,['차량번호_안전','차량번호','carNumber']); sw=get_sw_info({'SW_Safeview':r.get('SW_Safeview',r.get('app_Safeview','')),'SW_CPU':r.get('SW_CPU',r.get('app_CPU','')),'SW_MCU':r.get('SW_MCU',r.get('app_MCU','')),'SW_VPU1':r.get('SW_VPU1',r.get('app_VPU1','')),'SW_VPU2':r.get('SW_VPU2',r.get('app_VPU2','')),'SW_VPU3':r.get('SW_VPU3',r.get('app_VPU3','')),'SW_VPU4':r.get('SW_VPU4',r.get('app_VPU4','')),'carNumber':c_num,'dt_obj':pd.to_datetime(f"{r.get('shift_date_str','1970-01-01')} 08:30:00",errors='coerce')},sw_db_list); sb=get_valid_str(r,['출발_배터리_차량']); eb=get_valid_str(r,['종료_배터리_차량']); sk=r.get('출발_km','-'); ek=r.get('종료_km','-'); tk=r.get('총주행거리(km)','-')
            h3+=f"<tr><td style='font-weight:700;color:#475569;'>{r.get('운행일자','-')}</td><td style='font-weight:700;color:#0f172a;'>{c_num}</td><td>{get_valid_str(r,['출발자','Safe_Guard'])}</td><td style='font-weight:700;color:#4F46E5;'>{get_valid_str(r,['운행자'])}</td><td>{get_valid_str(r,['종료자'])}</td><td style='font-weight:700;color:#be185d;background-color:#fdf2f8;'>{cv}</td><td style='font-weight:700;color:#be185d;background-color:#fdf2f8;'>{pv}</td><td style='color:#64748b;'>{f'{int(float(sk)):,}' if sk!='-' else sk}</td><td style='color:#64748b;'>{f'{int(float(ek)):,}' if ek!='-' else ek}</td><td style='font-weight:700;color:#ea580c;background-color:#fffbeb;'>{f'{int(float(tk)):,}' if tk!='-' else tk}</td><td style='color:#64748b;'>{r.get('출발_시간','-')}</td><td style='color:#64748b;'>{r.get('종료_시간','-')}</td><td style='font-weight:700;color:#166534;'>{f'{int(float(sb))}%' if sb.replace('.','').isdigit() else sb}</td><td style='font-weight:700;color:#991b1b;'>{f'{int(float(eb))}%' if eb.replace('.','').isdigit() else eb}</td><td style='color:#64748b;font-size:11px;'>{sw.get('Safeview','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('CPU','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('MCU','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('VPU1','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('VPU2','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('VPU3','-')}</td><td style='color:#64748b;font-size:11px;'>{sw.get('VPU4','-')}</td><td style='text-align:left;white-space:normal;min-width:180px;color:#ef4444;'>{get_valid_str(r,['특이사항'])}</td></tr>"
        st.markdown(h3+"</tbody></table></div>",unsafe_allow_html=True)
    else: st.warning("기록된 운행 일지가 없습니다.")
