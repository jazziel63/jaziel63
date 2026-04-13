import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import requests

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")

# [사용자 시트 주소]
URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit"

def get_remote_ip():
    try:
        response = requests.get('https://api64.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return "IP 확인 불가"

def save_log_to_sheets(log_data):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        
        user_ip = get_remote_ip()
        log_data.insert(1, user_ip)
        
        sheet = client.open_by_url(URL).worksheet("log")
        sheet.append_row(log_data)
    except Exception as e:
        st.error(f"로그 기록 중 오류 발생: {e}")

def check_violation(full_car_no):
    try:
        kst = timezone(timedelta(hours=9))
        today_day = datetime.now(kst).day
        if today_day == 31: return False
        digits = [char for char in str(full_car_no) if char.isdigit()]
        if not digits: return False
        last_digit = int(digits[-1])
        if (today_day % 2 != last_digit % 2):
            return True
        return False
    except:
        return False

# --- 스타일 설정 ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-size: 0.95rem; }
    .main-title { font-size: 1.4rem !important; font-weight: bold; padding-bottom: 0.8rem; color: #31333F; }
    .violation-box { 
        background-color: #FFF0F0; color: #FF4B4B; font-weight: bold; 
        border: 2px solid #FF4B4B; padding: 12px; border-radius: 10px; 
        text-align: center; margin-bottom: 10px; 
    }
    div[data-testid="stNumberInput"] > label { display: none !important; }
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] { display: none !important; }
    .stNumberInput input { font-size: 1.2rem !important; height: 2.8rem !important; }
    /* 폼 테두리 제거 */
    [data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 학교 차량 조회 시스템</div>', unsafe_allow_html=True)

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

def reset_search():
    st.session_state["search_val"] = None
    st.session_state["search_submitted"] = False

if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0).fillna("-")

    # --- 엔터 키 지원을 위해 Form 사용 ---
    with st.form("search_form", clear_on_submit=False):
        search_val = st.number_input(
            label="차량번호조회", 
            label_visibility="collapsed",
            min_value=0, max_value=9999, value=None, step=1, format="%d",
            key="search_val", placeholder="차량 뒷번호 4자리를 입력하세요."
        )
        submit_button = st.form_submit_button("🔍 조회 결과 확인", use_container_width=True)

    # 조회 로직 실행
    if (submit_button or st.session_state["search_submitted"]) and search_val is not None:
        st.session_state["search_submitted"] = True
        search_num_str = str(int(search_val))
        search_input_4 = search_num_str.zfill(4)
        
        df['검색용번호'] = df['차량번호'].astype(str).str.replace(" ", "")
        results = df[df['검색용번호'].str.contains(search_input_4) | df['검색용번호'].str.endswith(search_num_str)].drop_duplicates()
        
        now = get_now_kst()
        
        if not results.empty:
            st.success(f"조회 결과 ({len(results)}건)")
            for i, res in results.iterrows():
                full_car_no = res.get('차량번호', '-')
                name = res.get('성명', '-')
                car_type = res.get('차량종류', '-')
                reason = str(res.get('제외사유', '-')).strip()
                
                is_v = check_violation(full_car_no)
                invalid_reasons = ["-", "해당없음", "정보 없음", "정보없음", ""]
                has_exception = reason not in invalid_reasons

                status_for_log = "정상"
                with st.expander(f"📍 {full_car_no} ({name})", expanded=True):
                    if has_exception:
                        st.info(f"✅ 정상 차량입니다. ({reason})")
                    elif is_v:
                        st.markdown('<div class="violation-box">⚠️ 위반 검토 대상입니다.</div>', unsafe_allow_html=True)
                        status_for_log = "위반 검토 대상"
                    else:
                        st.success("✅ 정상 차량입니다.")

                    st.write(f"**차주:** {name} | **차종:** {car_type}")
                    st.write(f"**제외사유:** {reason}")
                
                save_log_to_sheets([now, search_val, full_car_no, name, reason, "등록차량", status_for_log])
        else:
            st.error(f"❌ '{search_num_str}' 등록 정보가 없습니다.")
            is_v_unreg = check_violation(search_num_str)
            status_unreg = "위반 검토 대상(미등록)" if is_v_unreg else "정상(미등록)"
            
            if is_v_unreg:
                st.markdown(f'<div class="violation-box">⚠️ 위반 검토 대상입니다.(미등록)</div>', unsafe_allow_html=True)
            
            save_log_to_sheets([now, search_val, "정보없음", "정보없음", "정보없음", "미등록", status_unreg])

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 연결 오류가 발생했습니다.")