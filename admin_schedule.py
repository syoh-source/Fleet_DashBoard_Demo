import streamlit as st
import pandas as pd
import datetime
import time
import random
import re
import firebase_manager as fm
from chart_utils import get_korean_holidays, get_shift_date, draw_admin_preview_calendar
import admin_utils as utils

def get_premium_header(icon, title, color="#4F46E5"):
    return f"<div style='display: flex; align-items: center; margin-top: 10px; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #f1f5f9;'><div style='background: linear-gradient(135deg, {color}cc 0%, {color} 100%); color: white; width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 20px; margin-right: 12px; box-shadow: 0 4px 10px {color}40;'>{icon}</div><h3 style='margin: 0; color: #0f172a; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;'>{title}</h3></div>"

def draw_schedule_management(clean_df, sched_df, u_df, m_cars, m_drivers, kst_now):
    st.markdown(get_premium_header("🗓️", "배차 및 휴무 스케줄 통합 관리", "#10B981"), unsafe_allow_html=True)
    
    if 'draft_dict' not in st.session_state: st.session_state.draft_dict = {}
    if 'sim_range' not in st.session_state: st.session_state.sim_range = None
    if 'auto_sched_reasons' not in st.session_state: st.session_state.auto_sched_reasons = {}
    
    col_auto, col_assign, col_manual = st.columns(3)
    
    v_reg = st.session_state.get('view_region', '전체')
    v_shift = st.session_state.get('shift', '주간')
    u_role = st.session_state.get('user_role', 'user')

    valid_u_df = u_df.copy()
    
    if u_role != 'admin':
        if v_reg != '전체':
            valid_u_df = valid_u_df[valid_u_df['region'] == v_reg]
        shift_kw = '야간' if '야간' in v_shift else '주간'
        valid_u_df = valid_u_df[valid_u_df['shift'].fillna('').str.contains(shift_kw)]

    pure_drivers = [str(r.get('name')).strip() for _, r in valid_u_df.iterrows() if utils.parse_bool(r.get('can_view_dashboard')) and utils.parse_bool(r.get('is_driver')) and not utils.parse_bool(r.get('is_admin')) and not utils.parse_bool(r.get('is_support')) and pd.notna(r.get('name'))]
    assignable_all_drivers = sorted(list(set([str(r.get('name')).strip() for _, r in valid_u_df.iterrows() if utils.parse_bool(r.get('can_view_dashboard')) and (utils.parse_bool(r.get('is_driver')) or utils.parse_bool(r.get('is_support'))) and pd.notna(r.get('name'))])))

    with col_auto:
        st.markdown("<h4 style='color:#0f172a; font-weight:700; margin-bottom:15px;'>🤖 자동 배차 생성</h4>", unsafe_allow_html=True)
        with st.form("auto_sched_form"):
            a_dates = st.date_input("배정 기간 (시작일~종료일)", value=(kst_now.date(), kst_now.date() + datetime.timedelta(days=7)))
            a_avail_cars = st.multiselect("🚗 서비스 운영 차량 (일반 가용)", options=m_cars, default=m_cars[:5] if len(m_cars) >= 3 else m_cars)
            
            st.markdown("<div style='background-color:#eff6ff; padding:10px; border-radius:10px; margin: 10px 0;'><b>🛠️ 서비스 외 배차 (특수 임무 전담)</b></div>", unsafe_allow_html=True)
            ns_car = st.selectbox("특수 차량 선택", options=["선택안함"] + m_cars)
            ns_purpose = st.text_input("사용 목적 (달력 표시용)", placeholder="예: 데이터수집, VIP시승")
            ns_drivers = st.multiselect("전담 요원 지정 (동시 탑승)", options=pure_drivers)
            
            a_exclude = st.multiselect("배차 제외 인원", options=pure_drivers)
            a_exclude_direct = st.text_input("제외 직접 입력 (쉼표 구분)")
            a_weekdays = st.checkbox("☑️ 평일(공휴일 제외)만 배정", value=True)
            
            if st.form_submit_button("🔎 미리보기에 오토 추가", type="primary", use_container_width=True):
                if not a_avail_cars and ns_car == "선택안함": st.warning("차량을 최소 1대 이상 설정해주세요.")
                elif ns_car != "선택안함" and not ns_purpose.strip(): st.warning("서비스 외 배차의 '사용 목적'을 입력해주세요.")
                elif isinstance(a_dates, tuple) and len(a_dates) == 2:
                    d_start, d_end = a_dates
                    if st.session_state.sim_range:
                        st.session_state.sim_range = (min(st.session_state.sim_range[0], d_start.strftime('%Y-%m-%d')), max(st.session_state.sim_range[1], d_end.strftime('%Y-%m-%d')))
                    else:
                        st.session_state.sim_range = (d_start.strftime('%Y-%m-%d'), d_end.strftime('%Y-%m-%d'))
                        
                    final_excludes = a_exclude + [n.strip() for n in a_exclude_direct.split(',') if n.strip()]
                    
                    keys_to_remove = []
                    for (d, n), t in st.session_state.draft_dict.items():
                        if d_start.strftime('%Y-%m-%d') <= d <= d_end.strftime('%Y-%m-%d'):
                            if str(t).startswith('배정') or str(t).startswith('특수배차') or str(t).startswith('지정배차'): keys_to_remove.append((d, n))
                    for k in keys_to_remove: del st.session_state.draft_dict[k]
                    
                    for d_idx in range((d_end - d_start).days + 1):
                        d_str = (d_start + datetime.timedelta(days=d_idx)).strftime('%Y-%m-%d')
                        if d_str in st.session_state.auto_sched_reasons: del st.session_state.auto_sched_reasons[d_str]
                    
                    if not sched_df.empty:
                        for _, row in sched_df.iterrows():
                            s_type = str(row.get('type', '')).strip()
                            if s_type.startswith('배정') or s_type.startswith('특수배차') or s_type.startswith('지정배차'):
                                d_key = str(row.get('date')).strip()[:10]
                                if d_start.strftime('%Y-%m-%d') <= d_key <= d_end.strftime('%Y-%m-%d'):
                                    st.session_state.draft_dict[(d_key, str(row.get('name')).strip())] = 'DELETE'

                    effective_sched = {}
                    if not sched_df.empty:
                        for _, row in sched_df.iterrows():
                            d_key, n_key, s_type = str(row.get('date')).strip()[:10], str(row.get('name')).strip(), str(row.get('type', '')).strip()
                            if d_key not in effective_sched: effective_sched[d_key] = {}
                            effective_sched[d_key][n_key] = s_type
                            
                    for (d_str, name), s_type in st.session_state.draft_dict.items():
                        if d_str not in effective_sched: effective_sched[d_str] = {}
                        if s_type == 'DELETE':
                            if name in effective_sched[d_str]: del effective_sched[d_str][name]
                        else:
                            effective_sched[d_str][name] = s_type

                    busy_drivers, busy_cars = {}, {}
                    for d_key, day_sched in effective_sched.items():
                        busy_drivers[d_key], busy_cars[d_key] = set(), set()
                        for n_key, s_type in day_sched.items():
                            busy_drivers[d_key].add(n_key)
                            m = re.search(r'\((.*?)\)', s_type)
                            if m: busy_cars[d_key].add(m.group(1).strip())
                            
                    stats = {n: {'worked_dates': set(), 'last_car': None, 'car_counts_30': {c: 0 for c in m_cars}} for n in assignable_all_drivers}
                    
                    if not clean_df.empty:
                        history_df = clean_df.copy()
                        history_df['shift_date'] = pd.to_datetime(history_df['dt_obj'], errors='coerce').apply(get_shift_date)
                        
                        for _, r in history_df[history_df['shift_date'] >= (d_start - datetime.timedelta(days=40))].iterrows():
                            n, d, c = str(r['driverName']).strip(), r['shift_date'], str(r['carNumber']).strip()
                            if n in stats and pd.notnull(d):
                                stats[n]['worked_dates'].add(d)
                                if (d_start - d).days <= 30 and c in stats[n]['car_counts_30']: stats[n]['car_counts_30'][c] += 1
                                    
                        last_car_df = history_df.sort_values('dt_obj').drop_duplicates('driverName', keep='last')
                        for _, r in last_car_df.iterrows():
                            n, c = str(r['driverName']).strip(), str(r['carNumber']).strip()
                            if n in stats: stats[n]['last_car'] = c

                    for d_key in sorted(effective_sched.keys()):
                        day_sched = effective_sched[d_key]
                        try: d_obj = pd.to_datetime(d_key).date()
                        except: continue
                        if d_obj < d_start:
                            for n_key, s_type in day_sched.items():
                                if n_key in stats and ('배정' in s_type or '지정배차' in s_type or '특수배차' in s_type):
                                    stats[n_key]['worked_dates'].add(d_obj)
                                    m = re.search(r'\((.*?)\)', s_type)
                                    if m:
                                        c = m.group(1).strip()
                                        if c in stats[n_key]['car_counts_30']: stats[n_key]['car_counts_30'][c] += 1
                                        stats[n_key]['last_car'] = c 

                    curr = d_start
                    while curr <= d_end:
                        hols = get_korean_holidays(curr.year)
                        if a_weekdays and (curr.weekday() >= 5 or curr in hols): 
                            curr += datetime.timedelta(days=1); continue
                            
                        d_str = curr.strftime('%Y-%m-%d')
                        st.session_state.auto_sched_reasons[d_str] = {'selected': [], 'unselected': [], 'excluded': []}
                        
                        lookback_14, lookback_30 = curr - datetime.timedelta(days=14), curr - datetime.timedelta(days=30)
                        
                        avail_drivers = [n for n in pure_drivers if n not in busy_drivers.get(d_str, set()) and n not in final_excludes]
                        cars_today = [c for c in a_avail_cars if c not in busy_cars.get(d_str, set())]
                        prev_bday = curr - datetime.timedelta(days=1)
                        if a_weekdays:
                            while prev_bday.weekday() >= 5 or prev_bday in get_korean_holidays(prev_bday.year): prev_bday -= datetime.timedelta(days=1)
                        
                        def sort_key(n): 
                            return (1 if prev_bday in stats[n]['worked_dates'] else 0, sum(1 for d in stats[n]['worked_dates'] if lookback_30 <= d < curr), sum(1 for d in stats[n]['worked_dates'] if lookback_14 <= d < curr), max(stats[n]['worked_dates']).toordinal() if stats[n]['worked_dates'] else 0, random.random())
                        
                        if ns_car != "선택안함":
                            if ns_car in cars_today: cars_today.remove(ns_car)
                            avail_ns = [n for n in ns_drivers if n in avail_drivers]
                            for sel_ns in avail_ns:
                                st.session_state.auto_sched_reasons[d_str]['selected'].append({'name': sel_ns, 'car': ns_car, 'reason': f"⭐특수배차[{ns_purpose}]"})
                                st.session_state.draft_dict[(d_str, sel_ns)] = f'특수배차({ns_car}) [{ns_purpose}]'
                                stats[sel_ns]['worked_dates'].add(curr)
                                if ns_car in stats[sel_ns]['car_counts_30']: stats[sel_ns]['car_counts_30'][ns_car] += 1
                                stats[sel_ns]['last_car'] = ns_car
                                avail_drivers.remove(sel_ns) 
                            for sp_drv in ns_drivers:
                                if sp_drv in avail_drivers:
                                    avail_drivers.remove(sp_drv)
                                    st.session_state.auto_sched_reasons[d_str]['unselected'].append({'name': sp_drv, 'reason': "서비스 외 차량 전담 인원 (오늘은 대기)"})

                        avail_drivers.sort(key=sort_key)
                        selected, unselected = avail_drivers[:len(cars_today)], avail_drivers[len(cars_today):]
                            
                        assignments = {}
                        assigned_cars = set()
                        
                        for sel in selected:
                            last_c = stats[sel].get('last_car')
                            
                            # 🌟 E / U 교차 배정 1순위 탐색 로직 적용
                            last_prefix = str(last_c).strip()[0].upper() if last_c and last_c != "미정" else ""
                            target_prefix = 'U' if last_prefix == 'E' else ('E' if last_prefix == 'U' else '')
                            
                            valid_cars = [c for c in cars_today if c not in assigned_cars]
                            
                            # 1. 반대 알파벳이면서 내가 안 타본 차 우선 탐색
                            pref_cars = [c for c in valid_cars if str(c).strip()[0].upper() == target_prefix and c != last_c]
                            # 2. 반대 알파벳 차가 없다면 그냥 안 타본 차 탐색
                            diff_cars = [c for c in valid_cars if c != last_c]
                            
                            if pref_cars:
                                pref_cars.sort(key=lambda c: stats[sel]['car_counts_30'].get(c, 0))
                                chosen = pref_cars[0]
                            elif diff_cars:
                                diff_cars.sort(key=lambda c: stats[sel]['car_counts_30'].get(c, 0))
                                chosen = diff_cars[0]
                            else:
                                if valid_cars:
                                    valid_cars.sort(key=lambda c: stats[sel]['car_counts_30'].get(c, 0))
                                    chosen = valid_cars[0]
                                else:
                                    chosen = "미정"
                                    
                            assignments[sel] = chosen
                            if chosen != "미정":
                                assigned_cars.add(chosen)
                                
                        for sel in selected:
                            chosen = assignments[sel]
                            last_c = stats[sel].get('last_car')
                            
                            if chosen == last_c and chosen != "미정":
                                for other in selected:
                                    if other == sel: continue
                                    other_chosen = assignments[other]
                                    other_last_c = stats[other].get('last_car')
                                    
                                    if other_chosen != "미정":
                                        if other_chosen != last_c and chosen != other_last_c:
                                            assignments[sel] = other_chosen
                                            assignments[other] = chosen
                                            break
                                            
                        for sel in selected:
                            best_car = assignments[sel]
                            last_c = stats[sel].get('last_car')
                            count_14, count_30 = sum(1 for d in stats[sel]['worked_dates'] if lookback_14 <= d < curr), sum(1 for d in stats[sel]['worked_dates'] if lookback_30 <= d < curr)
                            
                            last_prefix = str(last_c).strip()[0].upper() if last_c and last_c != "미정" else ""
                            target_prefix = 'U' if last_prefix == 'E' else ('E' if last_prefix == 'U' else '')
                            
                            if best_car == last_c and best_car != "미정":
                                reason_txt = f"최근 30일간 {count_30}일 근무. (⚠️모든 차가 소진되어 동일차 연속 배정 불가피)"
                            else:
                                driven_count = stats[sel]['car_counts_30'].get(best_car, 0)
                                if str(best_car).strip()[0].upper() == target_prefix and target_prefix != "":
                                    reason_txt = f"최근 30일간 {count_30}일 근무. (E/U 교차 배정 완료 ✅ / 이 차량 30일내 탑승: {driven_count}회)"
                                else:
                                    reason_txt = f"최근 30일간 {count_30}일 근무. (이 차량 탑승: {driven_count}회 👉 타차량 균등배분 및 연속탑승 회피)"
                                
                            st.session_state.auto_sched_reasons[d_str]['selected'].append({'name': sel, 'car': best_car, 'reason': reason_txt})
                            st.session_state.draft_dict[(d_str, sel)] = f'배정({best_car})'
                            stats[sel]['worked_dates'].add(curr)
                            
                            if best_car != "미정": 
                                if best_car in stats[sel]['car_counts_30']: stats[sel]['car_counts_30'][best_car] += 1
                                stats[sel]['last_car'] = best_car 
                            
                        for unsel in unselected:
                            count_30 = sum(1 for d in stats[unsel]['worked_dates'] if lookback_30 <= d < curr)
                            worked_yesterday = 1 if prev_bday in stats[unsel]['worked_dates'] else 0
                            detail = "어제 출근함 (피로도 방어 휴식)" if worked_yesterday else "근무일수 초과로 우선순위 밀림"
                            st.session_state.auto_sched_reasons[d_str]['unselected'].append({'name': unsel, 'reason': f"최근 30일간 {count_30}일 근무. 👉 {detail}"})
                            
                        for exc in [n for n in pure_drivers if n in busy_drivers.get(d_str, set()) or n in final_excludes]:
                            st.session_state.auto_sched_reasons[d_str]['excluded'].append({'name': exc, 'reason': "관리자 제외 또는 기존 일정 존재"})
                        
                        curr += datetime.timedelta(days=1)
                    st.success("E/U 교차 배정 및 타차량 균등 배분이 완료되었습니다! 미리보기를 확인하세요.")
                    time.sleep(1.5)
                    st.rerun()

    with col_assign:
        st.markdown("<h4 style='color:#0f172a; font-weight:700; margin-bottom:15px;'>🎯 지정 배차 (수동)</h4>", unsafe_allow_html=True)
        with st.form("manual_assign_form", clear_on_submit=True):
            m_dates = st.date_input("지정 배차 기간", value=(kst_now.date(), kst_now.date()))
            m_names = st.multiselect("배정할 요원 (기사/지원)", options=assignable_all_drivers)
            m_car = st.selectbox("고정할 차량", options=m_cars if m_cars else ["차량없음"])
            m_purpose = st.text_input("지정 목적 (기본값: 지정배차)", placeholder="예: 지정배차, VIP수행")
            
            if st.form_submit_button("➕ 지정 배차 추가", use_container_width=True, type="primary"):
                if not m_names: st.warning("배정할 요원을 선택해주세요.")
                else:
                    d_start, d_end = m_dates if isinstance(m_dates, tuple) and len(m_dates) == 2 else (m_dates[0], m_dates[0]) if isinstance(m_dates, tuple) else (m_dates, m_dates)
                    st.session_state.sim_range = (min(st.session_state.sim_range[0], d_start.strftime('%Y-%m-%d')) if st.session_state.sim_range else d_start.strftime('%Y-%m-%d'), max(st.session_state.sim_range[1], d_end.strftime('%Y-%m-%d')) if st.session_state.sim_range else d_end.strftime('%Y-%m-%d'))
                    
                    curr = d_start
                    while curr <= d_end:
                        for nm in m_names: st.session_state.draft_dict[(curr.strftime('%Y-%m-%d'), nm)] = f'지정배차({m_car}) [{m_purpose.strip() or "지정배차"}]'
                        curr += datetime.timedelta(days=1)
                    st.success("지정 배차가 추가되었습니다!")
                    time.sleep(1)
                    st.rerun()

    with col_manual:
        st.markdown("<h4 style='color:#0f172a; font-weight:700; margin-bottom:15px;'>🏖️ 휴무/예외 등록</h4>", unsafe_allow_html=True)
        with st.form("manual_schedule_form", clear_on_submit=True):
            s_dates = st.date_input("기간 선택", value=(kst_now.date(), kst_now.date()))
            s_names = st.multiselect("요원 선택", assignable_all_drivers)
            s_type = st.text_input("일정 종류", placeholder="휴가, 예비군, 대기 등")
            s_skip_weekend = st.checkbox("☑️ 휴일(주말/공휴일) 제외", value=True)
            
            if st.form_submit_button("➕ 휴무/예외 추가", use_container_width=True):
                if not s_names or not s_type: st.warning("요원과 일정 종류를 모두 입력해주세요.")
                else:
                    d_start, d_end = s_dates if isinstance(s_dates, tuple) and len(s_dates) == 2 else (s_dates[0], s_dates[0]) if isinstance(s_dates, tuple) else (s_dates, s_dates)
                    st.session_state.sim_range = (min(st.session_state.sim_range[0], d_start.strftime('%Y-%m-%d')) if st.session_state.sim_range else d_start.strftime('%Y-%m-%d'), max(st.session_state.sim_range[1], d_end.strftime('%Y-%m-%d')) if st.session_state.sim_range else d_end.strftime('%Y-%m-%d'))
                    
                    curr = d_start
                    while curr <= d_end:
                        if s_skip_weekend and (curr.weekday() >= 5 or curr in get_korean_holidays(curr.year)): 
                            curr += datetime.timedelta(days=1); continue
                        for nm in s_names: st.session_state.draft_dict[(curr.strftime('%Y-%m-%d'), nm)] = s_type
                        curr += datetime.timedelta(days=1)
                    st.success("휴무가 추가되었습니다!")
                    time.sleep(1)
                    st.rerun()

    st.divider()

    c_title, c_btn1, c_btn2, c_btn3 = st.columns([2.5, 1.5, 1.5, 1.5])
    c_title.markdown(get_premium_header("👀", "스케줄 미리보기 및 저장", "#8B5CF6"), unsafe_allow_html=True)
    
    if c_btn1.button("🔄 자동/지정 미리보기 초기화", use_container_width=True): 
        st.session_state.draft_dict = {k: v for k, v in st.session_state.draft_dict.items() if not str(v).startswith('배정') and not str(v).startswith('지정배차') and not str(v).startswith('특수배차') and v != 'DELETE'}
        st.session_state.auto_sched_reasons = {}
        st.rerun()
        
    if c_btn2.button("🗑️ 선택기간 DB 완전 삭제", use_container_width=True):
        if st.session_state.sim_range:
            db = fm.init_firebase()
            for d_idx in range((datetime.datetime.strptime(st.session_state.sim_range[1], '%Y-%m-%d') - datetime.datetime.strptime(st.session_state.sim_range[0], '%Y-%m-%d')).days + 1):
                d_str = (datetime.datetime.strptime(st.session_state.sim_range[0], '%Y-%m-%d') + datetime.timedelta(days=d_idx)).strftime('%Y-%m-%d')
                for nm in assignable_all_drivers: db.collection('schedules').document(f"{d_str}_{nm}").delete()
            fm.trigger_db_update(); st.cache_data.clear()
            st.session_state.draft_dict = {}; st.session_state.auto_sched_reasons = {} 
            st.success("선택 기간의 모든 스케줄이 삭제되었습니다.")
            time.sleep(1.5)
            st.rerun()
        else: st.warning("위쪽 폼에서 기간을 지정하여 미리보기를 먼저 실행해주세요.")

    if c_btn3.button("✅ 변경사항 DB 최종 저장", type="primary", use_container_width=True):
        if not st.session_state.draft_dict: st.warning("저장할 변경사항이 없습니다.")
        else:
            db = fm.init_firebase()
            for (d, n), t in st.session_state.draft_dict.items():
                doc_id = f"{d}_{n}"
                if t == 'DELETE': db.collection('schedules').document(doc_id).delete()
                else: db.collection('schedules').document(doc_id).set({'date': d, 'name': n, 'type': t, 'updated_at': int(time.time())})
            
            if st.session_state.get('auto_sched_reasons'):
                for d_str, logs in st.session_state.auto_sched_reasons.items():
                    db.collection('schedule_logs').document(d_str).set({'logs': logs, 'updated_at': int(time.time())})
            
            fm.trigger_db_update(); st.cache_data.clear()
            st.session_state.draft_dict = {}; st.session_state.sim_range = None; st.session_state.auto_sched_reasons = {} 
            st.success("스케줄 및 배차 로그가 클라우드에 성공적으로 저장되었습니다!")
            time.sleep(1.5)
            st.rerun()
    
    draft_entries = [{'date': str(d)[:10], 'name': str(n).strip(), 'type': str(t).strip()} for (d, n), t in st.session_state.draft_dict.items() if t != 'DELETE']
    deleted_keys = set([(str(d)[:10], str(n).strip()) for (d, n), t in st.session_state.draft_dict.items() if t == 'DELETE'])
    
    min_date_str = st.session_state.sim_range[0] if st.session_state.sim_range and st.session_state.sim_range[0] < kst_now.date().strftime('%Y-%m-%d') else kst_now.date().strftime('%Y-%m-%d')

    if not sched_df.empty:
        preview_base = sched_df.copy()
        preview_base['date'] = preview_base['date'].astype(str).str.strip().str[:10]
        preview_base['name'] = preview_base['name'].astype(str).str.strip()
        preview_base = preview_base[(preview_base['date'] >= min_date_str) & (~preview_base.apply(lambda x: (str(x['date']), str(x['name'])) in deleted_keys, axis=1))]
        
        if draft_entries:
            draft_keys = set([(e['date'], e['name']) for e in draft_entries])
            final_preview_df = pd.concat([preview_base[~preview_base.apply(lambda x: (str(x['date']), str(x['name'])) in draft_keys, axis=1)], pd.DataFrame(draft_entries)], ignore_index=True)
        else: final_preview_df = preview_base
    else: final_preview_df = pd.DataFrame(draft_entries)

    draw_admin_preview_calendar(datetime.datetime.strptime(min_date_str, '%Y-%m-%d').date(), final_preview_df, clean_df)
    
    if st.session_state.get('auto_sched_reasons'):
        with st.expander("🤖 현재 작성 중인 배차 선정 근거 (미리보기)", expanded=False):
            st.info("💡 스케줄을 '최종 저장'하면 이 로그들은 아래의 [과거 로그 보관함]으로 영구 저장됩니다.")
            for d_str, logs in sorted(st.session_state.auto_sched_reasons.items()):
                st.markdown(f"##### 📅 {d_str} 배차 결과")
                st.markdown("**✅ 배정 완료**")
                for log in logs.get('selected', []): st.markdown(f"- 👤 **{log['name']}** (🚗 {log['car']}) 👉 {log['reason']}")
                if logs.get('unselected'):
                    st.markdown("**⏸️ 배정 대기 (휴식/밀림)**")
                    for log in logs['unselected']: st.markdown(f"- 👤 <span style='color:gray'>{log['name']}</span> 👉 {log['reason']}", unsafe_allow_html=True)
                if logs.get('excluded'):
                    st.markdown("**🚫 배정 제외**")
                    for log in logs['excluded']: st.markdown(f"- 👤 <span style='color:#ef4444'>{log['name']}</span> 👉 {log['reason']}", unsafe_allow_html=True)
                st.markdown("---")

    st.divider()

    st.markdown("#### 📂 클라우드 배차 근거 보관함 (영구 보존)")
    try: saved_logs_db = fm.load_data('schedule_logs')
    except: saved_logs_db = {}
    
    if not saved_logs_db: st.info("💡 아직 클라우드에 저장된 과거 배차 로그가 없습니다.")
    else:
        log_dates = sorted(list(saved_logs_db.keys()), reverse=True)
        sel_log_date = st.selectbox("🔎 조회할 배차 날짜를 선택하세요", options=log_dates)
        
        if sel_log_date:
            logs = saved_logs_db[sel_log_date].get('logs', {})
            with st.container(border=True):
                st.markdown(f"##### 📅 {sel_log_date} 배차 결과")
                st.markdown("**✅ 배정 완료**")
                for log in logs.get('selected', []): st.markdown(f"- 👤 **{log['name']}** (🚗 {log.get('car','알수없음')}) 👉 {log.get('reason','')}")
                if logs.get('unselected'):
                    st.markdown("**⏸️ 배정 대기**")
                    for log in logs['unselected']: st.markdown(f"- 👤 <span style='color:gray'>{log['name']}</span> 👉 {log.get('reason','')}", unsafe_allow_html=True)
                if logs.get('excluded'):
                    st.markdown("**🚫 배정 제외**")
                    for log in logs['excluded']: st.markdown(f"- 👤 <span style='color:#ef4444'>{log['name']}</span> 👉 {log.get('reason','')}", unsafe_allow_html=True)

    st.divider()

    st.markdown(get_premium_header("✏️", "기존 DB 스케줄 개별 수정/삭제", "#64748B"), unsafe_allow_html=True)
    if not sched_df.empty:
        edited_sched = st.data_editor(sched_df.sort_values('date', ascending=False).copy(), hide_index=True, use_container_width=True, num_rows="dynamic", column_config={"date": st.column_config.TextColumn("날짜", width="medium"), "name": st.column_config.TextColumn("이름", width="medium"), "type": st.column_config.TextColumn("일정 종류", width="large")}, key="sched_editor")
        if st.button("💾 스케줄 표 수정/삭제 DB 즉시 반영", type="primary"):
            db = fm.init_firebase()
            orig_keys = set(zip(sched_df['date'], sched_df['name']))
            curr_keys = set(zip(edited_sched['date'], edited_sched['name']))
            for d, n in (orig_keys - curr_keys): 
                db.collection('schedules').document(f"{d}_{n}").delete()
            for _, r in edited_sched.iterrows():
                if pd.notna(r['date']) and pd.notna(r['name']): 
                    db.collection('schedules').document(f"{str(r['date'])}_{str(r['name'])}").set({'date': str(r['date']), 'name': str(r['name']), 'type': str(r['type']), 'updated_at': int(time.time())})
            fm.trigger_db_update()
            st.cache_data.clear()
            st.success("개별 수정사항이 반영되었습니다!")
            time.sleep(1)
            st.rerun()
