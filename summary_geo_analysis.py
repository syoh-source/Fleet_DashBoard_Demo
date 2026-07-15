import streamlit as st; import pandas as pd; import pydeck as pdk; import re; import datetime; import numpy as np; import requests     
@st.cache_data(ttl=3600*24)
def get_korean_dong(lat,lng):
    try:
        res=requests.get(f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=15&addressdetails=1",headers={'User-Agent':'RideCounterDashboard/1.0'},timeout=3).json(); addr=res.get('address',{})
        dong=addr.get('quarter',addr.get('suburb',addr.get('town',addr.get('village','')))); gu=addr.get('borough',addr.get('city',''))
        return f"{gu} {dong}" if dong and gu and dong!=gu else (dong if dong else (f"{gu} 일대" if gu else "상세주소 미상"))
    except: return "주소 변환 지연"
@st.cache_data(show_spinner=False,ttl=3600)
def preprocess_geo_data(clean_df):
    df=clean_df.copy()
    def c_ms(v):
        if pd.isna(v) or v=="": return pd.NaT
        try: val=float(v); return pd.to_datetime(val*1000 if val<1e11 else val,unit='ms',utc=True).tz_convert('Asia/Seoul')
        except: return pd.NaT
    if 'ride_start_time' not in df.columns: df['ride_start_time']=np.nan
    if 'ride_end_time' not in df.columns: df['ride_end_time']=np.nan
    df['ride_start_kst']=df['ride_start_time'].apply(c_ms); df['ride_end_kst']=df['ride_end_time'].apply(c_ms)
    for c in ['latitude','longitude','end_latitude','end_longitude','route_path']:
        if c not in df.columns: df[c]=np.nan
    gdf=df.dropna(subset=['latitude','longitude']).copy()
    if gdf.empty: return gdf
    gdf['latitude']=pd.to_numeric(gdf['latitude'],errors='coerce'); gdf['longitude']=pd.to_numeric(gdf['longitude'],errors='coerce'); gdf['end_latitude']=pd.to_numeric(gdf['end_latitude'],errors='coerce'); gdf['end_longitude']=pd.to_numeric(gdf['end_longitude'],errors='coerce')
    gdf['call_id']=gdf.apply(lambda r: f"[{r.get('carNumber','차량미상')}] {r['ride_start_kst'].strftime('%Y-%m-%d %H:%M:%S')} 탑승 건" if pd.notna(r['ride_start_kst']) else f"[{r.get('carNumber','차량미상')}] 탑승 시간 미상 ({r.name}번)",axis=1)
    return gdf
def natural_sort_key(s): return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)',str(s))]
def draw_geo_view(clean_df,is_mobile):
    gdf=preprocess_geo_data(clean_df)
    if gdf.empty: st.info("💡 GPS 위치가 기록된 운행 데이터가 없습니다."); return
    mlat,mlng=float(gdf['latitude'].mean()),float(gdf['longitude'].mean())
    ucars=sorted(gdf['carNumber'].dropna().unique(),key=natural_sort_key); cp=[[227,26,28],[51,160,44],[31,120,180],[255,127,0],[106,61,154],[251,154,153],[177,89,40],[255,215,0]]; cm={c:cp[i%len(cp)] for i,c in enumerate(ucars)}
    scars=st.multiselect("🚗 조회할 차량을 선택하세요:",options=ucars,default=[])
    fgeo=gdf[gdf['carNumber'].isin(scars)].copy()
    pd_data=[]
    for _,r in fgeo.iterrows():
        rt=r.get('route_path')
        if isinstance(rt,list) and len(rt)>1:
            pc=[[float(pt['lng']),float(pt['lat'])] for pt in rt[::5] if isinstance(pt,dict) and 'lng' in pt and 'lat' in pt]
            if len(pc)>1: pd_data.append({"call_id":str(r['call_id']),"path":pc,"carNumber":str(r['carNumber']),"color":cm.get(r['carNumber'],[100,100,100])})
    pdf=pd.DataFrame(pd_data); fms='https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json'
    mt1,mt2,mt3=st.tabs(["📍 전체 위치","🔥 밀집 구역","🔦 상세 경로"])
    with mt1:
        if not fgeo.empty:
            ls=[]; s_s=fgeo[['longitude','latitude','call_id','carNumber']].dropna().reset_index(drop=True)
            ls.append(pdk.Layer("ScatterplotLayer",data=s_s,get_position='[longitude, latitude]',get_fill_color=[227,26,28,200],get_radius=15,radius_min_pixels=3,pickable=True,auto_highlight=True))
            s_e=fgeo[['end_longitude','end_latitude','call_id','carNumber']].dropna().reset_index(drop=True)
            if not s_e.empty: ls.append(pdk.Layer("ScatterplotLayer",data=s_e,get_position='[end_longitude, end_latitude]',get_fill_color=[31,120,180,200],get_radius=15,radius_min_pixels=3,pickable=True,auto_highlight=True))
            if not pdf.empty: ls.append(pdk.Layer("PathLayer",data=pdf,pickable=True,get_color="color",width_scale=1,width_min_pixels=2,get_path="path",get_width=4))
            st.caption("🔴 빨간점: 탑승지 / 🔵 파란점: 하차지")
            st.pydeck_chart(pdk.Deck(map_style=fms,initial_view_state=pdk.ViewState(latitude=mlat,longitude=mlng,zoom=12,pitch=0,bearing=0),layers=ls,tooltip={"text":"{call_id}"}))
        else: st.warning("차량을 선택하세요.")
    with mt2:
        if not fgeo.empty:
            s_s=fgeo[['longitude','latitude','call_id']].dropna().reset_index(drop=True); uim=st.radio("🎨 핫스팟 UI 스타일 선택",["🔥 부드러운 그라데이션 (Heatmap)","📊 3D 입체 빌딩 (Hexagon 3D)"],horizontal=True,key="hotspot_style_radio")
            if "Heatmap" in uim: hl=pdk.Layer("HeatmapLayer",data=s_s,get_position='[longitude, latitude]',radius_pixels=45,intensity=0.9,threshold=0.03); cp,cb=0,0
            else: cp,cb=50,-15; hl=pdk.Layer("HexagonLayer",data=s_s,get_position='[longitude, latitude]',radius=70,elevation_scale=15,elevation_range=[0,400],extruded=True,coverage=0.9,pickable=True,auto_highlight=True)
            st.pydeck_chart(pdk.Deck(map_style=fms,initial_view_state=pdk.ViewState(latitude=mlat,longitude=mlng,zoom=12.5,pitch=cp,bearing=cb),layers=[hl])); st.markdown("<br>💡 밀집구역 분석",unsafe_allow_html=True)
            p_df=fgeo[['latitude','longitude']].dropna().copy(); d_df=fgeo[['end_latitude','end_longitude']].dropna().copy()
            if not p_df.empty: p_df['lat_bin']=p_df['latitude'].round(3); p_df['lng_bin']=p_df['longitude'].round(3); tp=p_df.groupby(['lat_bin','lng_bin']).size().reset_index(name='count').sort_values('count',ascending=False).head(3)
            if not d_df.empty: d_df['lat_bin']=d_df['end_latitude'].round(3); d_df['lng_bin']=d_df['end_longitude'].round(3); tdo=d_df.groupby(['lat_bin','lng_bin']).size().reset_index(name='count').sort_values('count',ascending=False).head(3)
            hc1,hc2=st.columns(2)
            with hc1:
                st.markdown("<div style='background:#f0fdf4;padding:15px;border-radius:12px;border:1px solid #bbf7d0;'><strong style='color:#166534;'>🟢 가장 탑승이 많은 구역 TOP 3</strong>",unsafe_allow_html=True)
                if not p_df.empty:
                    for idx,r in enumerate(tp.itertuples()): st.markdown(f"{idx+1}. **{get_korean_dong(r.lat_bin,r.lng_bin)}** 주변 ({int(r.count)}건)")
                else: st.caption("기록 없음")
                st.markdown("</div>",unsafe_allow_html=True)
            with hc2:
                st.markdown("<div style='background:#eff6ff;padding:15px;border-radius:12px;border:1px solid #bfdbfe;'><strong style='color:#1e40af;'>🏁 가장 하차가 많은 구역 TOP 3</strong>",unsafe_allow_html=True)
                if not d_df.empty:
                    for idx,r in enumerate(tdo.itertuples()): st.markdown(f"{idx+1}. **{get_korean_dong(r.lat_bin,r.lng_bin)}** 주변 ({int(r.count)}건)")
                else: st.caption("기록 없음")
                st.markdown("</div>",unsafe_allow_html=True)
        else: st.warning("차량을 선택하세요.")
    with mt3:
        if not fgeo.empty:
            f2,f3,f4=st.columns(3)
            with f2: sd=st.selectbox("👤 운행 요원",["전체"]+sorted(fgeo['driverName'].dropna().unique().tolist()))
            t2=fgeo if sd=="전체" else fgeo[fgeo['driverName']==sd]
            with f3: stm=st.selectbox("⏰ 시간대",["전체"]+sorted(t2['time_bracket'].dropna().unique().tolist()))
            t3=t2 if stm=="전체" else t2[t2['time_bracket']==stm]
            with f4: si=st.selectbox("🚨 이슈 필터",["전체보기","⚠️ 이슈 발생 건만 보기"])
            im=(t3['이슈건수']>0)|(t3['통합_이슈상세'].fillna('').astype(str).str.strip()!='')
            t4=t3 if si=="전체보기" else t3[im]
            sci=sorted(t4['call_id'].dropna().unique().tolist(),key=natural_sort_key)
            if not sci: st.warning("조건에 맞는 호출 건이 없습니다.")
            else:
                co=["전체보기"]+sci; tid=st.session_state.get("saved_call_id"); didx=co.index(tid) if tid and tid in co else 0
                def ocs(): st.session_state["saved_call_id"]=st.session_state.call_id_selector
                sc=st.selectbox("🎯 표시할 호출 건 선택:",options=co,index=didx,key="call_id_selector",on_change=ocs); st.session_state["saved_call_id"]=sc; sl=[]
                if sc=="전체보기":
                    st.success(f"**🗺️ 현재 필터 조건에 해당하는 총 {len(t4)}건의 호출 궤적과 이슈를 모두 표시합니다.**")
                    sd=t4[['longitude','latitude','end_longitude','end_latitude','call_id','carNumber']].dropna(subset=['longitude','latitude']).copy().reset_index(drop=True); sd['tooltip_text']=sd['call_id']
                    if not sd.empty:
                        sl.append(pdk.Layer("ScatterplotLayer",data=sd,get_position='[longitude, latitude]',get_fill_color=[16,185,129,255],get_radius=15,radius_min_pixels=3,pickable=True))
                        ed=sd.dropna(subset=['end_longitude','end_latitude'])
                        if not ed.empty: sl.append(pdk.Layer("ScatterplotLayer",data=ed,get_position='[end_longitude, end_latitude]',get_fill_color=[59,130,246,255],get_radius=15,radius_min_pixels=3,pickable=True))
                    cin=t4['call_id'].tolist(); spd=pdf[pdf['call_id'].isin(cin)].reset_index(drop=True)
                    if not spd.empty: spd['tooltip_text']=spd['call_id']; sl.append(pdk.Layer("PathLayer",data=spd,get_color=[249,115,22,150],width_min_pixels=3,get_path="path",pickable=True))
                    ai=[]
                    for _,r in t4.iterrows():
                        ps=r.get('issue_pings',[]); ms=r.get('report_memos',{}); mi=str(ms['ADMIN_EDIT']).strip() if isinstance(ms,dict) and 'ADMIN_EDIT' in ms else ""
                        if isinstance(ps,list):
                            for p in ps:
                                if isinstance(p,dict) and 'lat' in p and 'lng' in p:
                                    pt=p.get('time')
                                    if mi: mt=f"{mi} (admin)"
                                    else: mv=ms.get(str(pt),ms.get(int(pt) if pd.notna(pt) else 0,"이슈 상세내용 미기입")) if isinstance(ms,dict) else (" / ".join(str(x) for x in ms) if isinstance(ms,list) else "이슈 상세내용 미기입"); mt=f"{mv} (app)" if mv!="이슈 상세내용 미기입" else mv
                                    ai.append({"longitude":float(p['lng']),"latitude":float(p['lat']),"tooltip_text":f"[{r['call_id']}] 🚨 {mt}"})
                    if ai: sl.append(pdk.Layer("ScatterplotLayer",data=pd.DataFrame(ai),get_position='[longitude, latitude]',get_fill_color=[239,68,68,255],get_radius=15,radius_min_pixels=4,pickable=True))
                    mls=float(sd['latitude'].mean()) if not sd.empty else mlat; mlngs=float(sd['longitude'].mean()) if not sd.empty else mlng
                    st.pydeck_chart(pdk.Deck(map_style=fms,initial_view_state=pdk.ViewState(latitude=mls,longitude=mlngs,zoom=12,pitch=0,bearing=0),layers=sl,tooltip={"text":"{tooltip_text}"}))
                else:
                    sr=t4[t4['call_id']==sc]
                    if not sr.empty and pd.notna(sr['end_longitude'].iloc[0]):
                        pts=sr['ride_start_kst'].iloc[0].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(sr['ride_start_kst'].iloc[0]) else "시간 미상"
                        dts=sr['ride_end_kst'].iloc[0].strftime('%Y-%m-%d %H:%M:%S') if pd.notna(sr['ride_end_kst'].iloc[0]) else "시간 미상"
                        ip=sr['issue_pings'].iloc[0] if 'issue_pings' in sr.columns else []; rm=sr['report_memos'].iloc[0] if 'report_memos' in sr.columns else {}
                        mi=str(rm['ADMIN_EDIT']).strip() if isinstance(rm,dict) and 'ADMIN_EDIT' in rm else ""; its=""
                        if sr['이슈건수'].iloc[0]>0:
                            ts=[pd.to_datetime(int(ping['time']),unit='ms',utc=True).tz_convert('Asia/Seoul').strftime('%H:%M:%S') for ping in ip if isinstance(ping,dict) and 'time' in ping] if isinstance(ip,list) else []
                            its=f" ➡️ :red[**🚨 이슈발생: {', '.join(ts)}**]" if ts else f" ➡️ :red[**🚨 이슈발생 (시간 미상)**]"
                        st.success(f"**🟢 탑승:** {pts} ➡️ **🏁 하차:** {dts} {its}")
                        gsl,gslg,gel,gelg=float(sr['latitude'].iloc[0]),float(sr['longitude'].iloc[0]),float(sr['end_latitude'].iloc[0]),float(sr['end_longitude'].iloc[0])
                        ch=f"<div style='font-size:13px;color:#475569;margin-top:10px;margin-bottom:15px;padding:15px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;line-height:1.8;'><div>🟢 <b>탑승지:</b> <a href='https://www.google.com/maps/search/?api=1&query={gsl},{gslg}' target='_blank' style='color:#2563eb;text-decoration:none;'><b>{gsl:.6f}, {gslg:.6f}</b></a> <span style='color:#94a3b8;font-size:11px;'>(클릭 구글 맵)</span></div><div>🏁 <b>하차지:</b> <a href='https://www.google.com/maps/search/?api=1&query={gel},{gelg}' target='_blank' style='color:#2563eb;text-decoration:none;'><b>{gel:.6f}, {gelg:.6f}</b></a></div>"
                        pi=[]
                        if isinstance(ip,list) and len(ip)>0:
                            ch+="<hr style='margin:8px 0;border:0;border-top:1px dashed #cbd5e1;'>"
                            for idx,p in enumerate(ip):
                                if isinstance(p,dict) and 'lat' in p and 'lng' in p:
                                    lat,lng=float(p['lat']),float(p['lng']); pt=p.get('time')
                                    if mi: mt=f"{mi} (admin)"
                                    else:
                                        mv="내용 미기입"
                                        if isinstance(rm,dict): mv=rm.get(str(pt),rm.get(int(pt) if pd.notna(pt) else 0,"내용 미기입"))
                                        elif isinstance(rm,list): mv=" / ".join([str(x) for x in rm])
                                        mt=f"{mv} (app)" if mv!="내용 미기입" else mv
                                    ch+=f"<div style='margin-top:6px;'>🚨 <b>{idx+1}번 이슈:</b> <a href='https://www.google.com/maps/search/?api=1&query={lat},{lng}' target='_blank' style='color:#ef4444;text-decoration:none;'><b>{lat:.6f}, {lng:.6f}</b></a> <span style='margin-left:8px;font-size:13px;color:#b91c1c;font-weight:600;background:#fee2e2;padding:2px 8px;border-radius:6px;'>📝 {mt}</span></div>"
                                    pi.append({"longitude":lng,"latitude":lat,"tooltip_text":f"🚨 {idx+1}번 이슈: {mt}"})
                        ch+="</div>"; st.markdown(ch,unsafe_allow_html=True)
                        if isinstance(ip,list) and len(ip)>0:
                            st.markdown("<div style='margin-top:15px;margin-bottom:5px;font-weight:700;color:#ef4444;'>📸 이슈 위치 (로드뷰)</div>",unsafe_allow_html=True); cs=st.columns(min(len(ip),4))
                            for idx,p in enumerate(ip[:4]):
                                if isinstance(p,dict) and 'lat' in p and 'lng' in p:
                                    with cs[idx]: st.link_button(f"👁️ {idx+1}번 로드뷰",f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={p['lat']},{p['lng']}",use_container_width=True)
                        ss=sr[['longitude','latitude','end_longitude','end_latitude','call_id','carNumber']].copy().reset_index(drop=True); ss['tooltip_text']=ss['call_id']
                        sl.append(pdk.Layer("ScatterplotLayer",data=ss,get_position='[longitude, latitude]',get_fill_color=[16,185,129,255],get_radius=15,radius_min_pixels=3,pickable=True))
                        sl.append(pdk.Layer("ScatterplotLayer",data=ss,get_position='[end_longitude, end_latitude]',get_fill_color=[59,130,246,255],get_radius=15,radius_min_pixels=3,pickable=True))
                        if not pdf.empty:
                            spdf=pdf[pdf['call_id']==sc].reset_index(drop=True)
                            if not spdf.empty: spdf['tooltip_text']=spdf['call_id']; sl.append(pdk.Layer("PathLayer",data=spdf,get_color=[249,115,22,220],width_min_pixels=4,get_path="path",pickable=True))
                        idf=pd.DataFrame(pi)
                        if not idf.empty: sl.append(pdk.Layer("ScatterplotLayer",data=idf,get_position='[longitude, latitude]',get_fill_color=[239,68,68,255],get_radius=15,radius_min_pixels=3,pickable=True))
                        st.pydeck_chart(pdk.Deck(map_style=fms,initial_view_state=pdk.ViewState(latitude=float(ss['latitude'].iloc[0]),longitude=float(ss['longitude'].iloc[0]),zoom=14,pitch=0,bearing=0),layers=sl,tooltip={"text":"{tooltip_text}"}))
        else: st.warning("차량을 선택하세요.")
