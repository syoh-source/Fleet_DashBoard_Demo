import streamlit as st
import admin_tabs as tabs
import time
import firebase_manager as fm
import os
import io
import zipfile
import json
import datetime

def json_default(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return str(obj)

def draw_admin_tab(clean_df, df_drive, u_df, sched_df, m_cars, m_drivers, kst_now):
    # 🔒 1. 2차 비밀번호 보안 로직
    if not st.session_state.get('settings_unlocked', False):
        pw = st.text_input("2차 비밀번호", type="password")
        if st.button("잠금 해제 🔓"):
            if pw == "2106": 
                st.session_state.settings_unlocked = True
                st.rerun()
            else: 
                st.error("비밀번호 불일치")
        return

    # 🔓 2. 잠금 해제 시 화면
    else:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info("🚨 **[관리자 모드 활성화]** 데이터의 수정, 저장 시 로컬 DB(json_DB)에 즉시 반영됩니다.")
        with col2:
            if st.button("🚪 설정 닫기", use_container_width=True): 
                st.session_state.settings_unlocked = False
                st.rerun()
                
        # =================================================================
        # 👑 [최고관리자 전용] 시스템 코어 제어 (Master Control)
        # =================================================================
        if st.session_state.get('user_id') == "syoh@swm.ai":
            st.markdown("---")
            with st.expander("👑 최고관리자 전용 코어 제어 (Master Control)", expanded=True):
                st.warning("⚠️ **주의:** 데이터베이스를 가져와 최신화합니다.")
                
                if st.button("🔥 전체 데이터 강제 재동기화 (Master Sync)"):
                    with st.spinner("DB에서 모든 데이터를 완전히 새로 다운로드합니다..."):
                        try:
                            fm.sync_only_new_data(force_full=True)
                            st.cache_resource.clear()
                            st.cache_data.clear()
                            st.success("✅ DB 원본과 100% 동일하게 강제 동기화되었습니다!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"동기화 실패: {e}")
                
                st.divider()
                
                # 🌟 버튼 B: [전체 DB 백업 다운로드] (.zip 백업)
                st.markdown("### 💾 전체 DB 다운로드 (로컬 백업용)")
                st.info("💡 파이어베이스에 저장된 순수 운행 데이터(Ride Logs, Driving Logs)만 추출하여 압축(ZIP) 다운로드합니다. (개인정보 보호 적용)")
                
                try:
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr("ride_logs.json", json.dumps(fm.get_ride_logs(), ensure_ascii=False, indent=2, default=json_default))
                        zip_file.writestr("driving_logs.json", json.dumps(fm.get_driving_logs(), ensure_ascii=False, indent=2, default=json_default))
                    
                    st.download_button(
                        label="📥 핵심 DB 백업 다운로드 (.zip)",
                        data=zip_buffer.getvalue(),
                        file_name=f"RideCounter_Core_Backup_{kst_now.strftime('%Y%m%d_%H%M')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"압축 파일 생성 중 오류: {e}")
                    
            st.markdown("<br>", unsafe_allow_html=True)
        # =================================================================
        
        # 📂 3. 탭 구성 및 각 모듈 연결
        admin_tabs = st.tabs([
            "👥 권한/명단 관리", 
            "🗓️ 배차 통합 관리", 
            "🚗 운영 차량 관리", 
            "🗄️ 데이터 수정/관리"
        ])
        
        with admin_tabs[0]:
            tabs.draw_user_management(u_df, m_cars, m_drivers)
            
        with admin_tabs[1]:
            tabs.draw_schedule_management(clean_df, sched_df, u_df, m_cars, m_drivers, kst_now)
            
        with admin_tabs[2]:
            tabs.draw_fleet_management(m_cars, m_drivers)
            
        with admin_tabs[3]:
            tabs.draw_data_management(clean_df, df_drive, m_cars, m_drivers, kst_now)
