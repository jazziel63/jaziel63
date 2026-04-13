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

# --- 1. 접속자 IP를 가져오는 함수 ---
def get_remote_ip():
    try:
        # 외부 API를 통해 접속자의 공인 IP를 가져옵니다.
        response = requests.get('https://api64.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return "IP 확인 불가"

# --- 2. 구글 시트 로그 저장 함수 (보안 키 오류 방지 포함) ---
def save_log_to_sheets(log_data):
    try:
        # 서비스 계정 인증 범위 설정
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # [중요] Secrets에서 가져온 키의 가짜 줄바꿈(\\n)을 진짜 줄바꿈(\n)으로 변환
        info = st.secrets["gcp_service_account"].to_dict()
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        creds = Credentials.from_service_account_info(info, scopes=scope)
        client = gspread.authorize(creds)
        
        # 접속 IP 가져오기 및 로그 데이터에 삽입 (일시 다음 칸에 삽입)
        user_ip = get_remote_ip()
        log_data.insert(1, user_ip)
        
        # 시트 URL로 열기 및 'log' 워크시트 선택
        sheet = client.open_by_url(URL).worksheet("log")
        sheet.append_row(log_data)
    except Exception as e:
        # 로그 저장이 실패해도 서비스는 계속 돌아가게 에러만 표시
        st.error(f"로그 기록 중 오류 발생: {e}")

# --- 스타일 설정 ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-size: 0.95rem; }
    .main-title { font-size: 1.4rem !important; font-weight: bold; padding-bottom: 0.8rem; color: #31333F; }
    .stNumberInput label { font-size: 1.0rem !important; font-weight: bold !important; }
    .stNumberInput input { font-size: 1.2rem !important; height: 2.8rem !important; -moz-appearance: textfield; }
    .stNumberInput input::-webkit-outer-spin-button, .stNumberInput input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    button[data-testid="stNumberInputStepDown"], button[data-testid="stNumberInputStepUp"] { display: none !important; }
    .stButton button { width: 100%; height: 2.8rem !important; font-size: 1.1rem !important; font-weight: bold !important; }
    .st-expander p { font-size: 1.0rem !important; line-height: 1.4; margin-bottom: 0.3rem; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 차량 번호 조회 시스템</div>', unsafe_allow_html=True)

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
    df = conn.read(spreadsheet=URL, ttl=0).fillna("정보 없음")

    search_val = st.number_input(
        "차량 뒷번호 입력",
        min_value=0,
        max_value=9999,
        value=None,
        step=1,
        format="%d",
        key="search_val",
        placeholder="차량 뒷번호 4자리 입력하세요."
    )

    submit_button = st.button("🔍 조회하기")

    if (submit_button or st.session_state["search_submitted"]) and search_val is not None:
        st.session_state["search_submitted"] = True
        
        search_num_str = str(int(search_val))
        search_input_4 = search_num_str.zfill(4)
        
        df['검색용번호'] = df['차량번호'].astype(str).str.replace(" ", "")
        
        results = df[
            df['검색용번호'].str.contains(search_input_4) | 
            df['검색용번호'].str.endswith(search_num_str)
        ].drop_duplicates()
        
        now = get_now_kst()
        
        if not results.empty:
            st.success(f"검색 결과 {len(results)}건")
            for i, res in results.iterrows():
                full_car_no = res.get('차량번호', '정보 없음')
                name = res.get('성명', '정보 없음')
                car_type = res.get('차량종류', '정보 없음')
                reason = res.get('제외사유', '정보 없음')
                
                with st.expander(f"📍 {full_car_no} ({name})", expanded=True):
                    st.write(f"**차주:** {name} | **차종:** {car_type}")
                    st.write(f"**제외사유:** {reason}")
                
                # [로그 저장] 시트의 'log' 탭으로 전송 (IP는 함수 내부에서 추가됨)
                save_log_to_sheets([now, search_val, full_car_no, name, reason, "등록차량"])
        else:
            st.error(f"❌ '{search_num_str}' 등록 정보 없음")
            # [로그 저장] 미등록 차량 정보 시트 전송
            save_log_to_sheets([now, search_val, "정보없음", "정보없음", "정보없음", "미등록"])

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")