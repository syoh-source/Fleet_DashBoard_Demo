def init_firebase(): return None
def authenticate_user(uid, pw): return False, {}, "해당 환경에서는 실제 로그인을 지원하지 않습니다. (portfolio / trial 사용)"
def create_user(*args): return False, "해당 환경에서는 가입이 불가합니다."
def request_account_change(*args): return False, "해당 환경에서는 변경이 불가합니다."
def get_master_data(): return None, {'cars': [], 'drivers': []}
def get_all_users(): return []
def get_ride_logs(): return []
def get_driving_logs(): return []
def get_schedules(): return []
def sync_only_new_data(*args, **kwargs): pass
def load_data(*args): return {}
def trigger_db_update(): pass
