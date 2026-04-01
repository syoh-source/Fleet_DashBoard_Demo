import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import requests
import streamlit as st

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("firebase_key.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

def get_db():
    return init_firebase()

# --- 1. 회원 관리 ---
def create_user(user_id, password, name, position):
    db = get_db()
    try:
        user_ref = db.collection('users').document(user_id)
        if user_ref.get().exists: return False, "이미 존재하는 아이디입니다."
        user_ref.set({
            'password': password, 'name': name, 'position': position,
            'role': 'user', 'is_approved': False, 'created_at': firestore.SERVER_TIMESTAMP
        })
        return True, "가입 신청 완료!"
    except: return False, "서버 연결 오류"

def authenticate_user(user_id, password):
    if user_id == "syoh@swm.ai" and password == "0105*":
        return True, {'role': 'admin', 'name': '최고관리자', 'is_approved': True}, "성공"
    db = get_db()
    try:
        user_ref = db.collection('users').document(user_id).get()
        if not user_ref.exists: return False, None, "아이디 없음"
        data = user_ref.to_dict()
        if data.get('password') != password: return False, None, "비번 틀림"
        if not data.get('is_approved', False): return False, None, "승인 대기중"
        return True, data, "성공"
    except: return False, None, "연결 지연"

def get_all_users():
    db = get_db()
    try:
        docs = db.collection('users').get()
        return [{'user_id': d.id, **d.to_dict()} for d in docs]
    except: return []

def update_user_approval(user_id, is_approved):
    get_db().collection('users').document(user_id).update({'is_approved': is_approved})

def delete_user(user_id):
    get_db().collection('users').document(user_id).delete()

# --- 2. 기상청 날씨 ---
def get_gangnam_weather():
    try:
        kst = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')
        if kst.minute < 40: kst -= pd.Timedelta(hours=1)
        api = "wjBTMKih4%2FtIu0puLg%2F04%2FSw7VSQsJbdmZgrXjwUtpJ44YrEEtXWXxjPCyla576KMKCkRLI5gtgFOIVcUlMzQg%3D%3D"
        url = f"https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst?serviceKey={api}&pageNo=1&numOfRows=10&dataType=JSON&base_date={kst.strftime('%Y%m%d')}&base_time={kst.strftime('%H00')}&nx=61&ny=126"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            items = res.json().get('response', {}).get('body', {}).get('items', {}).get('item', [])
            return {i['category']: i['obsrValue'] for i in items}
    except: return None

# --- 3. 데이터 로드 및 관리 ---
def get_master_data():
    db = get_db()
    try:
        doc_ref = db.collection('settings').document('master_data')
        doc = doc_ref.get()
        if doc.exists: return doc_ref, doc.to_dict()
        def_data = {'cars': [], 'drivers': []}
        doc_ref.set(def_data)
        return doc_ref, def_data
    except: return None, {'cars': [], 'drivers': []}

def update_master_data(cars, drivers):
    get_db().collection('settings').document('master_data').update({'cars': cars, 'drivers': drivers})

def get_ride_logs():
    db = get_db()
    try:
        docs = db.collection('ride_logs').get()
        res = []
        for d in docs:
            it = d.to_dict(); it['doc_id'] = d.id 
            if 'remark' not in it: it['remark'] = ""
            if 'callCount' not in it: it['callCount'] = 0
            if 'passengers' not in it: it['passengers'] = 0
            res.append(it)
        return res
    except: return []

def delete_ride_log(doc_id):
    get_db().collection('ride_logs').document(doc_id).delete()

def update_ride_remark(doc_id, new_remark):
    get_db().collection('ride_logs').document(doc_id).update({'remark': new_remark})

def delete_logs_by_field(field_name, value):
    db = get_db()
    try:
        docs = db.collection('ride_logs').where(field_name, '==', value).get()
        for d in docs: db.collection('ride_logs').document(d.id).delete()
    except Exception as e: print(f"오류: {e}")
