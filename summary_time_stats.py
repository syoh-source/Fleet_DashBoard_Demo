import streamlit as st
import pandas as pd
import plotly.express as px
from chart_utils import apply_modern_theme

def draw_time_stats_view(cdf, ism):
    th = [22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
    co = [f"{h:02d}시~{0 if h==23 else h+1:02d}시" for h in th]
    
    if cdf.empty:
        td = pd.DataFrame(columns=['time_bracket', 'duration_min'])
        hm = pd.DataFrame({'hour': th, 'is_manual': '🚕 정상 운행', 'callCount': 0})
        hm['시간표시'] = hm['hour'].apply(lambda h: f"{h:02d}시~{0 if h==23 else h+1:02d}시")
        tbd = pd.DataFrame({'time_bracket': ["04~22시(4,800원)", "22~23시(5,800원)", "23~02시(6,700원)", "02~04시(5,800원)"], 'is_manual': '🚕 정상 운행', 'callCount': 0})
        pd_df = pd.DataFrame({'chart_category': ['기록없음'], 'callCount': [1]})
        wd = pd.DataFrame({'weekday': ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'], 'is_manual': '🚕 정상 운행', 'callCount': 0})
        pv = pd.DataFrame(0, index=['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'], columns=[f"{h:02d}시" for h in th])
    else:
        cdf['callCount'] = pd.to_numeric(cdf['callCount'], errors='coerce').fillna(0)
        cdf['revenue'] = pd.to_numeric(cdf['revenue'], errors='coerce').fillna(0)
        vd = cdf[cdf['duration_min'] > 0].copy()
        td = vd.groupby('time_bracket')['duration_min'].mean().round(1).reset_index() if not vd.empty else pd.DataFrame(columns=['time_bracket', 'duration_min'])
        
        bh = pd.DataFrame({'hour': th})
        hr = cdf.groupby(['hour', 'is_manual'])['callCount'].sum().reset_index()
        hm = pd.merge(bh, hr, on='hour', how='left').fillna({'callCount': 0, 'is_manual': '🚕 정상 운행'})
        hm['시간표시'] = hm['hour'].apply(lambda h: f"{h:02d}시~{0 if h==23 else h+1:02d}시")
        
        tbd = cdf.groupby(['time_bracket', 'is_manual'])['callCount'].sum().reset_index()
        pd_df = cdf.groupby('chart_category')['callCount'].sum().reset_index()
        
        wm = {0: '월요일', 1: '화요일', 2: '수요일', 3: '목요일', 4: '금요일', 5: '토요일', 6: '일요일'}
        cdf['weekday'] = pd.to_datetime(cdf['shift_date']).dt.dayofweek.map(wm)
        wd = cdf.groupby(['weekday', 'is_manual'])['callCount'].sum().reset_index()
        
        ed = cdf.groupby(['weekday', 'hour'])['revenue'].sum().reset_index()
        ed['hour_str'] = ed['hour'].apply(lambda x: f"{x:02d}시")
        pv = ed.pivot(index='weekday', columns='hour_str', values='revenue').fillna(0)
        pv = pv.reindex(['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'])
        ah = [f"{h:02d}시" for h in th]
        vh = [c for c in ah if c in pv.columns]
        pv = pv.reindex(columns=vh).fillna(0)

    fhs = px.bar(hm, x='시간표시', y='callCount', color='is_manual', text_auto=True, color_discrete_map={'🚕 정상 운행': '#4F46E5', '📦 일괄 입력': '#F59E0B'}, category_orders={"시간표시": co})
    fhs.update_layout(dragmode=False, xaxis_title="시간", yaxis_title="호출 수(건)", xaxis_tickangle=-45, margin=dict(t=30, b=20))
    fhs.update_traces(textfont=dict(weight="bold", size=10), textposition="outside", textangle=0, cliponaxis=False)
    max_fhs = hm['callCount'].max()
    fhs.update_yaxes(range=[0, max_fhs * 1.3 if max_fhs > 0 else 10], fixedrange=True)
    
    fb = px.bar(tbd, x='time_bracket', y='callCount', color='is_manual', text_auto=True, color_discrete_map={'🚕 정상 운행': '#10B981', '📦 일괄 입력': '#64748B'}, category_orders={"time_bracket": ["04~22시(4,800원)", "22~23시(5,800원)", "23~02시(6,700원)", "02~04시(5,800원)"]})
    fb.update_layout(dragmode=False, xaxis_title="시간구간", yaxis_title="호출 수(건)", margin=dict(t=30, b=20), xaxis_tickangle=0)
    fb.update_traces(textfont=dict(weight="bold", size=11), textposition="outside", textangle=0, cliponaxis=False)
    max_fb = tbd['callCount'].max()
    fb.update_yaxes(range=[0, max_fb * 1.3 if max_fb > 0 else 10], fixedrange=True)
    
    fp = px.pie(pd_df, values='callCount', names='chart_category', hole=0.5)
    fp.update_traces(textposition='inside', textinfo='percent+label', textfont=dict(weight="bold", color="white"), marker=dict(line=dict(color='#ffffff', width=2)))
    fp.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", dragmode=False)
    
    fw = px.bar(wd, x='weekday', y='callCount', color='is_manual', text_auto=True, color_discrete_map={'🚕 정상 운행': '#8B5CF6', '📦 일괄 입력': '#CBD5E1'}, category_orders={"weekday": ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']})
    fw.update_layout(dragmode=False, xaxis_title="요일", yaxis_title="호출 수(건)", margin=dict(t=30, b=20), xaxis_tickangle=0)
    fw.update_traces(textfont=dict(weight="bold", size=11), textposition="outside", textangle=0, cliponaxis=False)
    max_fw = wd['callCount'].max()
    fw.update_yaxes(range=[0, max_fw * 1.3 if max_fw > 0 else 10], fixedrange=True)
    
    fhm = px.imshow(pv, text_auto=True, aspect="auto", color_continuous_scale='YlOrRd', labels=dict(x="시간대", y="요일", color="수입(원)"))
    fhm.update_traces(texttemplate="%{z:,.0f}", textfont=dict(size=10))
    fhm.update_layout(xaxis_title="시간대", yaxis_title="요일", margin=dict(t=10, b=10), dragmode=False, coloraxis_showscale=False)
    
    if ism:
        st.markdown("#### ⏰ 요금 구간별")
        st.plotly_chart(apply_modern_theme(fb), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("#### 🌙 시간별 호출 패턴")
        st.plotly_chart(apply_modern_theme(fhs), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("#### 📅 요일별 호출 추이")
        st.plotly_chart(apply_modern_theme(fw), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("#### 💎 수입 효율 (무상 제외)")
        st.plotly_chart(apply_modern_theme(fhm), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("#### ⏱️ 소요시간")
        if not td.empty: st.dataframe(td.rename(columns={'time_bracket': '구간', 'duration_min': '평균(분)'}), hide_index=True, use_container_width=True)
        else: st.caption("기록 없음")
        st.divider()
        st.markdown("<h5 style='text-align:center;'>🥧 탑승인원</h5>", unsafe_allow_html=True)
        st.plotly_chart(fp, use_container_width=True, config={'displayModeBar': False})
    else:
        r1c1, r1c2 = st.columns([2, 3])
        with r1c1:
            st.markdown("<div style='font-size:16px; font-weight:800; margin-bottom:10px;'>⏰ 요금 구간별 통계</div>", unsafe_allow_html=True)
            st.plotly_chart(apply_modern_theme(fb), use_container_width=True, config={'displayModeBar': False})
        with r1c2:
            st.markdown("<div style='font-size:16px; font-weight:800; margin-bottom:10px;'>🌙 시간별 통계</div>", unsafe_allow_html=True)
            st.plotly_chart(apply_modern_theme(fhs), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("<div style='font-size:16px; font-weight:800; margin-bottom:10px;'>💎 수입 효율 히트맵 (주간 무상 시간대 제외)</div>", unsafe_allow_html=True)
        st.plotly_chart(apply_modern_theme(fhm), use_container_width=True, config={'displayModeBar': False})
        st.divider()
        r2c1, r2c2 = st.columns([1.5, 1.5])
        with r2c1:
            st.markdown("<div style='font-size:16px; font-weight:800; margin-bottom:12px;'>⏱️ 구간별 평균 소요시간</div>", unsafe_allow_html=True)
            if not td.empty:
                ht = "<div style='background:white; border-radius:12px; border:1px solid #e2e8f0; padding:5px;'><table style='width:100%; border-collapse:collapse; font-size:13px; text-align:center;'><thead><tr><th style='background:#f8fafc; padding:12px 5px; border-bottom:2px solid #e2e8f0; font-weight:700;'>구간</th><th style='background:#f8fafc; padding:12px 5px; border-bottom:2px solid #e2e8f0; font-weight:700;'>소요(분)</th></tr></thead><tbody>"
                for _, r in td.iterrows(): ht += f"<tr><td style='padding:12px 5px; border-bottom:1px solid #f1f5f9; font-weight:600;'>{r['time_bracket']}</td><td style='padding:12px 5px; border-bottom:1px solid #f1f5f9;'><span style='color:#2563EB; font-weight:800; font-size:14px;'>{r['duration_min']}</span></td></tr>"
                st.markdown(ht + "</tbody></table></div>", unsafe_allow_html=True)
            else: st.caption("기록 없음")
        with r2c2:
            st.markdown("<div style='text-align:center; font-size:16px; font-weight:800; margin-bottom:10px;'>🥧 탑승인원</div>", unsafe_allow_html=True)
            st.plotly_chart(fp, use_container_width=True, config={'displayModeBar': False})
        st.divider()
        st.markdown("<div style='font-size:16px; font-weight:800; margin-bottom:10px;'>📅 요일별 호출 추이</div>", unsafe_allow_html=True)
        st.plotly_chart(apply_modern_theme(fw), use_container_width=True, config={'displayModeBar': False})
