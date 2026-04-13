import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import gspread
from google.oauth2.service_account import Credentials
import requests

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")

# [사용자 시트 주소]
URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit"

# --- 구글 시트 연결 함수 ---
def get_gspread_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        secrets_dict = st.secrets["gcp_service_account"]
        info = {k: v for k, v in secrets_dict.items()}
        if "private_key" in info:
            p_key = info["private_key"].strip().replace("\\n", "\n")
            if (p_key.startswith('"') and p_key.endswith('"')) or (p_key.startswith("'") and p_key.endswith("'")):
                p_key = p_key[1:-1].strip()
            p_key = p_key.replace("\r", "")
            info["private_key"] = p_key
        creds = Credentials.from_service_account_info(info, scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"인증 정보 로드 실패: {e}")
        return None

def get_remote_ip():
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return "IP 확인 불가"

def save_log_to_sheets(client, log_data):
    try:
        user_ip = get_remote_ip()
        log_data.insert(1, user_ip)
        sheet = client.open_by_url(URL).worksheet("log")
        sheet.append_row(log_data)
    except Exception as e:
        st.error(f"로그 기록 중 오류 발생: {e}")

def get_violation_info(full_car_no):
    try:
        kst = timezone(timedelta(hours=9))
        today_day = datetime.now(kst).day
        if today_day == 31:
            return False, "(31일 모든 차량 운행 가능)"
        is_today_odd = (today_day % 2 != 0)
        day_type_str = "(홀수차 운행일)" if is_today_odd else "(짝수차 운행일)"
        digits = [char for char in str(full_car_no) if char.isdigit()]
        if not digits: return False, day_type_str
        last_digit = int(digits[-1])
        is_violation = (today_day % 2 != last_digit % 2)
        return is_violation, day_type_str
    except:
        return False, ""

# --- 스타일 설정 (+, - 버튼 제거 및 최적화) ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-size: 0.92rem; }
    .main-title { font-size: 1.3rem !important; font-weight: bold; padding-bottom: 0.8rem; color: #31333F; }
    
    /* 결과 박스 스타일 */
    .violation-box, .normal-box { 
        font-weight: bold; padding: 10px; border-radius: 10px; text-align: center; 
        margin-top: 8px; margin-bottom: 8px; white-space: nowrap; overflow: hidden;
    }
    .violation-box { background-color: #FFF0F0; color: #FF4B4B; border: 2px solid #FF4B4B; }
    .normal-box { background-color: #F0F8FF; color: #1E90FF; border: 2px solid #1E90FF; }
    
    /* [수정] 입력창에서 +, - 버튼과 스피너 제거 */
    div[data-testid="InputInstructions"] { display: none !important; }
    div[data-testid="stNumberInput"] > label { display: none !important; }
    
    /* 크롬/사파리 등 브라우저 기본 스피너 제거 */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    
    /* 스트림릿 전용 +, - 스텝 버튼 강제 숨김 */
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] { display: none !important; }
    
    /* 입력창 내부 패딩 조정으로 버튼 빈자리 메우기 */
    .stNumberInput input { 
        font-size: 1.1rem !important; 
        height: 2.6rem !important; 
        padding-right: 10px !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 학교 차량 조회 시스템</div>', unsafe_allow_html=True)

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

def reset_search():
    st.session_state["search_val"] = None

try:
    client = get_gspread_client()
    if client:
        sheet = client.open_by_url(URL).get_worksheet(0)
        data = sheet.get_all_records()
        df = pd.DataFrame(data).fillna("-")

        # 입력창 (+, - 버튼이 CSS로 숨겨짐)
        search_val = st.number_input(
            label="차량번호조회", label_visibility="collapsed",
            min_value=0, max_value=9999, value=None, step=1, format="%d",
            key="search_val", placeholder="차량 뒷번호 4자리를 입력하세요."
        )

        st.button("🔍 조회 결과 확인", use_container_width=True)

        if search_val:
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
                    category = res.get('구분', '-')
                    car_type = res.get('차량종류', '-')
                    reason = str(res.get('제외사유', '-')).strip()
                    is_v, day_info = get_violation_info(full_car_no)
                    has_exception = reason not in ["-", "해당없음", "정보 없음", "정보없음", ""]

                    with st.expander(f"📍 {full_car_no} ({name})", expanded=True):
                        st.write(f"**차주:** {name} | **구분:** {category} | **차종:** {car_type}")
                        st.write(f"**제외사유:** {reason}")

                    if has_exception:
                        st.markdown(f'<div class="normal-box">✅ 정상 차량 ({reason})</div>', unsafe_allow_html=True)
                        status_for_log = f"정상 ({reason})"
                    elif is_v:
                        st.markdown(f'<div class="violation-box">⚠️ 위반 검토 대상 {day_info}</div>', unsafe_allow_html=True)
                        status_for_log = f"위반 검토 대상 {day_info}"
                    else:
                        st.markdown(f'<div class="normal-box">✅ 정상 차량 {day_info}</div>', unsafe_allow_html=True)
                        status_for_log = f"정상 {day_info}"
                    save_log_to_sheets(client, [now, search_val, full_car_no, name, category, reason, "등록차량", status_for_log])
            else:
                st.info("ℹ️ 미등록 차량입니다.")
                is_v_unreg, day_info_unreg = get_violation_info(search_num_str)
                if is_v_unreg:
                    st.markdown(f'<div class="violation-box">⚠️ 위반 검토 대상 {day_info_unreg}</div>', unsafe_allow_html=True)
                    status_unreg = f"위반 검토 대상(미등록) {day_info_unreg}"
                else:
                    st.markdown(f'<div class="normal-box">✅ 정상 차량 {day_info_unreg}</div>', unsafe_allow_html=True)
                    status_unreg = f"정상(미등록) {day_info_unreg}"
                save_log_to_sheets(client, [now, search_val, "정보없음", "정보없음", "정보없음", "정보없음", "미등록", status_unreg])

            st.divider()
            st.button("🔄 다시 조회하기", on_click=reset_search, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ 연결 오류가 발생했습니다. 원인: {e}")