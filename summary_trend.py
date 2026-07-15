import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from chart_utils import apply_modern_theme
import datetime

def draw_trend_view(clean_df, df_drive_merged, is_mobile):
    st.markdown("**📈 일일 운행 및 운영 효율 추이**")
    
    cdf = clean_df.copy()
    if cdf.empty:
        d_end = datetime.date.today()
        pdf = pd.DataFrame({'shift_date': [d_end - datetime.timedelta(days=i) for i in range(6, -1, -1)]})
        pdf['shift_date'] = pd.to_datetime(pdf['shift_date'])
        pdf['x_label'] = pdf['shift_date'].dt.strftime('%m/%d')
        for col in ['총주행거리(km)', 'callCount', 'carCount', 'calls_per_car', '평균대기분', '평균소요분']: pdf[col] = 0
        for col in ['callCount_line', 'calls_per_car_line', '평균대기분_line', '평균소요분_line', 'call_trend', 'cpc_trend', 'idle_trend', 'dur_trend']: pdf[col] = np.nan
        for c in ['text_dist', 'text_car', 'text_c1', 'text_cpc', 'text_dur', 'text_idle']: pdf[c] = ""
    else:
        cdf['shift_date'] = cdf.get('shift_date', cdf.get('날짜', pd.to_datetime(cdf.get('dt_obj', 'today')).dt.strftime('%Y-%m-%d')))
        for c in ['revenue', 'callCount', 'passengers', 'duration_min']: cdf[c] = cdf.get(c, 0)
        cdf['carNumber'] = cdf.get('carNumber', 'Unknown')
        
        rd = cdf.groupby('shift_date').agg(callCount=('callCount', 'sum'), carCount=('carNumber', 'nunique'), paxCount=('passengers', 'sum'), revenue=('revenue', 'sum')).reset_index()
        rd['shift_date'] = pd.to_datetime(rd['shift_date'])
        
        if not df_drive_merged.empty and 'shift_date' in df_drive_merged.columns:
            ddm = df_drive_merged.copy()
            ddm['date_dt'] = pd.to_datetime(ddm['shift_date'], errors='coerce')
            dd = ddm.groupby('date_dt')['총주행거리(km)'].sum().reset_index()
            md = pd.merge(rd, dd, left_on='shift_date', right_on='date_dt', how='outer')
            md['shift_date'] = pd.to_datetime(md['shift_date'].combine_first(md['date_dt']))
            md = md.fillna(0)
        else: 
            md = rd.copy()
            md['총주행거리(km)'] = 0
            
        vd = cdf[cdf['duration_min'] > 0].copy()
        if not vd.empty:
            ddly = vd.groupby('shift_date')['duration_min'].mean().round(1).reset_index(name='평균소요분')
            ddly['shift_date'] = pd.to_datetime(ddly['shift_date'])
            vd['dt_obj'] = pd.to_datetime(vd.get('ride_start_time', vd['shift_date']), unit='ms', errors='coerce').fillna(pd.to_datetime(vd['shift_date']))
            vd['driverName'] = vd.get('driverName', vd.get('운전자', 'Unknown'))
            di = vd.sort_values(['driverName', 'shift_date', 'dt_obj']).copy()
            di['end_time'] = di['dt_obj'] + pd.to_timedelta(di['duration_min'], unit='m')
            di['next_start'] = di.groupby(['driverName', 'shift_date'])['dt_obj'].shift(-1)
            di['idle_min'] = (di['next_start'] - di['end_time']).dt.total_seconds() / 60
            vi = di[(di['idle_min'] >= 0) & (di['idle_min'] <= 180)]
            idly = vi.groupby('shift_date')['idle_min'].mean().round(1).reset_index(name='평균대기분')
            idly['shift_date'] = pd.to_datetime(idly['shift_date'])
            md = pd.merge(md, ddly, on='shift_date', how='left')
            md = pd.merge(md, idly, on='shift_date', how='left')
        else: 
            md['평균소요분'], md['평균대기분'] = 0, 0
            
        md = md.fillna(0)
        md['carCount'] = md['carCount'].replace(0, 1)
        md['calls_per_car'] = (md['callCount'] / md['carCount']).round(1)
        md = md.sort_values('shift_date')
        
        pdf = md.copy()
        pdf['x_label'] = pdf['shift_date'].dt.strftime('%m/%d')
        
        for c in ['callCount', 'calls_per_car', '평균소요분', '평균대기분']: 
            pdf[f"{c}_line"] = np.where(pdf[c] <= 0, np.nan, pdf[c])
            
        pdf['text_dist'] = pdf['총주행거리(km)'].apply(lambda x: f"{int(x)}" if x > 0 else "")
        pdf['text_car'] = pdf['carCount'].apply(lambda x: f"{int(x)}" if x > 0 else "")
        pdf['text_c1'] = pdf['callCount'].apply(lambda x: f"{int(x)}" if x > 0 else "")
        pdf['text_cpc'] = pdf['calls_per_car'].apply(lambda x: f"{x}" if x > 0 else "")
        pdf['text_dur'] = pdf['평균소요분'].apply(lambda x: f" {x} " if x > 0 else "")
        pdf['text_idle'] = pdf['평균대기분'].apply(lambda x: f" {x} " if x > 0 else "")
        
        def gt(y):
            ya = np.array(y, dtype=float)
            id = np.arange(len(ya))
            m = ~np.isnan(ya) & (ya > 0)
            r = np.full(len(ya), np.nan)
            if m.sum() > 1: 
                z = np.polyfit(id[m], ya[m], 1)
                p = np.poly1d(z)
                r[np.where(m)[0][0]:np.where(m)[0][-1] + 1] = p(id[np.where(m)[0][0]:np.where(m)[0][-1] + 1])
            return r
            
        pdf['call_trend'] = gt(pdf['callCount_line'])
        pdf['cpc_trend'] = gt(pdf['calls_per_car_line'])
        pdf['idle_trend'] = gt(pdf['평균대기분_line'])
        pdf['dur_trend'] = gt(pdf['평균소요분_line'])

    if is_mobile:
        f1 = make_subplots(specs=[[{"secondary_y": True}]])
        f1.add_trace(go.Bar(x=pdf['x_label'], y=pdf['총주행거리(km)'], name="주행거리", marker_color="#3B82F6"), secondary_y=False)
        f1.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['callCount_line'], name="호출건수", mode="lines+markers", line=dict(color="#F97316", width=3)), secondary_y=True)
        f1.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1), dragmode=False, margin=dict(t=10, b=10))
        st.plotly_chart(f1, use_container_width=True, config={'displayModeBar': False})
        
        f2 = make_subplots(specs=[[{"secondary_y": True}]])
        f2.add_trace(go.Bar(x=pdf['x_label'], y=pdf['carCount'], name="운행차량", marker_color="#10B981"), secondary_y=False)
        f2.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['calls_per_car_line'], name="대당호출", mode="lines+markers", line=dict(color="#8B5CF6", width=3)), secondary_y=True)
        f2.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1), dragmode=False, margin=dict(t=10, b=10))
        st.plotly_chart(f2, use_container_width=True, config={'displayModeBar': False})
        
        f3 = make_subplots(specs=[[{"secondary_y": True}]])
        f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['평균대기분_line'], name="대기(분)", mode="lines+markers", line=dict(color="#EF4444", width=3)), secondary_y=False)
        f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['평균소요분_line'], name="소요(분)", mode="lines+markers", line=dict(color="#2563EB", width=3)), secondary_y=True)
        f3.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1), dragmode=False, margin=dict(t=10, b=10))
        st.plotly_chart(f3, use_container_width=True, config={'displayModeBar': False})
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.caption("🚕 [총 호출 수 vs 총 주행거리]")
            md, mc = pdf['총주행거리(km)'].max(), pdf['callCount'].max()
            f1 = make_subplots(specs=[[{"secondary_y": True}]])
            f1.add_trace(go.Bar(x=pdf['x_label'], y=pdf['총주행거리(km)'], name="주행거리", marker_color="#3B82F6", text=pdf['text_dist'], textposition="outside", textfont=dict(color="#2563EB", size=12)), secondary_y=False)
            f1.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['callCount_line'], name="호출건수", mode="lines+markers+text", text=pdf['text_c1'], textposition="top center", textfont=dict(color="#C2410C", size=13), line=dict(color="#F97316", width=3), marker=dict(size=8), connectgaps=True), secondary_y=True)
            f1.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['call_trend'], name="추세", mode="lines", line=dict(color="#C2410C", width=2, dash="dot"), hoverinfo="skip"), secondary_y=True)
            f1.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1), dragmode=False, margin=dict(t=30, b=20), height=450)
            f1.update_yaxes(title_text="주행거리", secondary_y=False, showgrid=False, range=[0, (md * 1.3) if md > 0 else 10], fixedrange=True)
            f1.update_yaxes(title_text="호출건수", secondary_y=True, showgrid=True, gridcolor="#E2E8F0", range=[0, (mc * 1.3) if mc > 0 else 10], fixedrange=True)
            f1.update_traces(cliponaxis=False)
            st.plotly_chart(f1, use_container_width=True, config={'displayModeBar': False})
            
        with c2:
            st.caption("📈 [운행 차량 대수 vs 대당 평균 호출]")
            mca, mpc = pdf['carCount'].max(), pdf['calls_per_car'].max()
            f2 = make_subplots(specs=[[{"secondary_y": True}]])
            f2.add_trace(go.Bar(x=pdf['x_label'], y=pdf['carCount'], name="운행차량", marker_color="#10B981", text=pdf['text_car'], textposition="outside", textfont=dict(color="#059669", size=12)), secondary_y=False)
            f2.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['calls_per_car_line'], name="대당호출", mode="lines+markers+text", text=pdf['text_cpc'], textposition="top center", textfont=dict(color="#312E81", size=13), line=dict(color="#8B5CF6", width=3), marker=dict(size=8), connectgaps=True), secondary_y=True)
            f2.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['cpc_trend'], name="추세", mode="lines", line=dict(color="#6D28D9", width=2, dash="dot"), hoverinfo="skip"), secondary_y=True)
            f2.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.1), margin=dict(t=30, b=20), dragmode=False, height=450)
            f2.update_yaxes(title_text="차량(대)", secondary_y=False, showgrid=False, range=[0, (mca * 1.3) if mca > 0 else 10], fixedrange=True)
            f2.update_yaxes(title_text="대당호출", secondary_y=True, showgrid=True, gridcolor="#E2E8F0", range=[0, (mpc * 1.3) if mpc > 0 else 10], fixedrange=True)
            f2.update_traces(cliponaxis=False)
            st.plotly_chart(f2, use_container_width=True, config={'displayModeBar': False})
            
        st.divider()
        c3, c4 = st.columns(2)
        with c3:
            st.caption("⏱️ [공차시간 vs 소요시간]")
            mi, mdur = pdf['평균대기분'].max(), pdf['평균소요분'].max()
            f3 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05)
            f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['평균대기분_line'], name="대기(분)", mode="lines+markers+text", text=pdf['text_idle'], textposition="top center", textfont=dict(color="#991B1B", size=13), line=dict(color="#EF4444", width=3), marker=dict(size=8), connectgaps=True), row=1, col=1)
            f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['idle_trend'], name="추세", mode="lines", line=dict(color="#991B1B", width=2, dash="dot"), hoverinfo="skip"), row=1, col=1)
            f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['평균소요분_line'], name="소요(분)", mode="lines+markers+text", text=pdf['text_dur'], textposition="top center", textfont=dict(color="#1E3A8A", size=13), line=dict(color="#2563EB", width=3), marker=dict(size=8), connectgaps=True), row=2, col=1)
            f3.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['dur_trend'], name="추세", mode="lines", line=dict(color="#1E3A8A", width=2, dash="dot"), hoverinfo="skip"), row=2, col=1)
            f3.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.12), dragmode=False, margin=dict(t=30, b=20), height=450)
            f3.update_yaxes(title_text="대기(분)", showgrid=True, gridcolor="#E2E8F0", range=[0, (mi * 1.3) if mi > 0 else 10], fixedrange=True, row=1, col=1)
            f3.update_yaxes(title_text="소요(분)", showgrid=True, gridcolor="#E2E8F0", range=[0, (mdur * 1.3) if mdur > 0 else 10], fixedrange=True, row=2, col=1)
            f3.update_xaxes(showgrid=False, fixedrange=True)
            f3.update_traces(cliponaxis=False)
            st.plotly_chart(f3, use_container_width=True, config={'displayModeBar': False})
            
        with c4:
            st.caption("🚕 [호출 건수 vs 평균 소요시간]")
            mc4, md4 = pdf['callCount'].max(), pdf['평균소요분'].max()
            f4 = make_subplots(specs=[[{"secondary_y": True}]])
            f4.add_trace(go.Bar(x=pdf['x_label'], y=pdf['callCount'], name="호출건수", text=pdf['text_c1'], textposition="outside", textfont=dict(color="#7C3AED", size=12), marker_color="#8B5CF6"), secondary_y=False)
            f4.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['평균소요분_line'], name="소요(분)", mode="lines+markers+text", text=pdf['text_dur'], textposition="top center", textfont=dict(color="#854D0E", size=13), line=dict(color="#EAB308", width=3), marker=dict(size=8), connectgaps=True), secondary_y=True)
            f4.add_trace(go.Scatter(x=pdf['x_label'], y=pdf['dur_trend'], name="추세", mode="lines", line=dict(color="#A16207", width=2, dash="dot"), hoverinfo="skip"), secondary_y=True)
            f4.update_layout(plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.12), dragmode=False, margin=dict(t=30, b=20), height=450)
            f4.update_yaxes(title_text="호출", secondary_y=False, showgrid=False, range=[0, (mc4 * 1.3) if mc4 > 0 else 10], fixedrange=True)
            f4.update_yaxes(title_text="소요(분)", secondary_y=True, showgrid=True, gridcolor="#E2E8F0", range=[0, (md4 * 1.3) if md4 > 0 else 10], fixedrange=True)
            f4.update_traces(cliponaxis=False)
            st.plotly_chart(f4, use_container_width=True, config={'displayModeBar': False})
