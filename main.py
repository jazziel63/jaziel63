import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")

# --- 스타일 설정 ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-size: 0.95rem; }
    .main-title { font-size: 1.4rem !important; font-weight: bold; padding-bottom: 0.8rem; color: #31333F; }
    .stNumberInput label { font-size: 1.0rem !important; font-weight: bold !important; }
    .stNumberInput input { font-size: 1.2rem !important; height: 2.6rem !important; }
    .stButton button { width: 100%; height: 2.8rem !important; font-size: 1.1rem !important; font-weight: bold !important; }
    /* 숫자 입력창 옆의 + / - 버튼 숨기기 */
    button.step-up, button.step-down { display: none; }
    div[data-testid="stNumberInputStepDown"], div[data-testid="stNumberInputStepUp"] { display: none; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 차량 번호 조회 시스템</div>', unsafe_allow_html=True)

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit?gid=1417331015#gid=1417331015"

def reset_search():
    st.session_state["search_val"] = 0
    st.session_state["search_submitted"] = False

if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0).fillna("정보 없음")

    # [핵심 수정] st.number_input을 사용하여 숫자 패드 강제 호출
    # value=None으로 설정하여 처음엔 비워둡니다.
    search_val = st.number_input(
        "차량번호 뒷자리 입력",
        min_value=0,
        max_value=9999,
        value=None,
        step=1,
        format="%d",
        key="search_val",
        placeholder="4자리 숫자 입력"
    )

    submit_button = st.button("🔍 조회하기")

    if (submit_button or st.session_state["search_submitted"]) and search_val is not None:
        st.session_state["search_submitted"] = True
        
        # [중요] 숫자를 다시 4자리 문자열로 변환 (예: 822 -> "0822")
        # 이 과정이 있어야 0으로 시작하는 번호도 검색이 됩니다.
        search_input = str(int(search_val)).zfill(4)
        
        # 만약 사용자가 3자리만 입력하고 싶어할 수도 있으므로 zfill 없이도 검색 시도
        search_input_3 = str(int(search_val))
        
        df['검색용번호'] = df['차량번호'].astype(str).str.replace(" ", "")
        
        # 4자리(0포함) 또는 입력한 숫자 자체가 포함된 경우 검색
        results = df[
            df['검색용번호'].str.contains(search_input) | 
            df['검색용번호'].str.endswith(search_input_3)
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
                
                try:
                    log_entry = f"{now},{search_input},{full_car_no},{name},{car_type},{reason},등록차량\n"
                    with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
                except: pass
        else:
            st.error(f"❌ '{search_input_3}' 등록 정보 없음")
            try:
                log_entry = f"{now},{search_input_3},정보없음,정보없음,정보없음,정보없음,미등록\n"
                with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
            except: pass

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")