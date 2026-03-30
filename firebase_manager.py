import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import requests

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 🔐 회원 관리 (Auth) 함수
# ==========================================
def create_user(user_id, password, name, position):
    user_ref = db.collection('users').document(user_id)
    if user_ref.get().exists:
        return False, "이미 존재하는 아이디(이메일)입니다."
    
    user_ref.set({
        'password': password,
        'name': name,
        'position': position,
        'role': 'user',
        'is_approved': False,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return True, "가입 신청 완료! 관리자 승인을 기다려주세요."

def authenticate_user(user_id, password):
    # 🌟 최고 관리자 (마스터 키 변경 적용!)
    if user_id == "syoh@swm.ai" and password == "0105*":
        return True, {'role': 'admin', 'name': '최고관리자', 'is_approved': True}, "성공"
    
    user_ref = db.collection('users').document(user_id).get()
    if not user_ref.exists:
        return False, None, "아이디가 존재하지 않습니다."
    
    user_data = user_ref.to_dict()
    if user_data['password'] != password:
        return False, None, "비밀번호가 틀렸습니다."
    if not user_data.get('is_approved', False):
        return False, None, "관리자 승인 대기 중입니다. (접근 불가)"
        
    return True, user_data, "성공"

def get_all_users():
    docs = db.collection('users').stream()
    users = []
    for d in docs:
        data = d.to_dict()
        data['user_id'] = d.id
        users.append(data)
    return users

def update_user_approval(user_id, is_approved):
    db.collection('users').document(user_id).update({'is_approved': is_approved})

def delete_user(user_id):
    db.collection('users').document(user_id).delete()

# ==========================================
# 📊 기존 데이터 관리 함수들
# ==========================================
def get_gangnam_weather():
    try:
        nx, ny = 61, 126
        kst_now = pd.Timestamp.utcnow().tz_convert('Asia/Seoul')
        minute = kst_now.minute
        if minute < 40: kst_now = kst_now - pd.Timedelta(hours=1)
        base_date = kst_now.strftime("%Y%m%d")
        base_time = kst_now.strftime("%H00")
        api_key = "wjBTMKih4%2FtIu0puLg%2F04%2FSw7VSQsJbdmZgrXjwUtpJ44YrEEtXWXxjPCyla576KMKCkRLI5gtgFOIVcUlMzQg%3D%3D"
        url = f"https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst?serviceKey={api_key}&pageNo=1&numOfRows=10&dataType=JSON&base_date={base_date}&base_time={base_time}&nx={nx}&ny={ny}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            weather_data = {}
            for item in items: weather_data[item['category']] = item['obsrValue']
            return weather_data
    except Exception as e: return None
    return None

def get_master_data():
    doc_ref = db.collection('settings').document('master_data')
    doc = doc_ref.get()
    if doc.exists: return doc_ref, doc.to_dict()
    else:
        default_data = {'cars': ["자율택시 01호"], 'drivers': ["홍길동"]}
        doc_ref.set(default_data)
        return doc_ref, default_data

def update_master_data(cars, drivers):
    db.collection('settings').document('master_data').update({'cars': cars, 'drivers': drivers})

def get_ride_logs():
    docs = db.collection('ride_logs').stream()
    data_list = []
    for doc in docs:
        item = doc.to_dict()
        item['doc_id'] = doc.id 
        if 'remark' not in item: item['remark'] = ""
        if 'callCount' not in item: item['callCount'] = 0
        if 'passengers' not in item: item['passengers'] = 0
        data_list.append(item)
    return data_list

def delete_ride_log(doc_id):
    db.collection('ride_logs').document(doc_id).delete()

def update_ride_remark(doc_id, new_remark):
    db.collection('ride_logs').document(doc_id).update({'remark': new_remark})
