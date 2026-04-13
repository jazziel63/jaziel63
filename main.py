import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")

# --- 스타일 설정: +, - 버튼 및 스피너 완전 제거 ---
st.markdown("""
    <style>
    html, body, [class*="css"]  { font-size: 0.95rem; }
    .main-title { font-size: 1.4rem !important; font-weight: bold; padding-bottom: 0.8rem; color: #31333F; }
    
    /* 숫자 입력창 라벨 및 높이 조절 */
    .stNumberInput label { font-size: 1.0rem !important; font-weight: bold !important; }
    .stNumberInput input { 
        font-size: 1.2rem !important; 
        height: 2.8rem !important; 
        -moz-appearance: textfield; 
    }

    /* 브라우저 기본 숫자 화살표 제거 */
    .stNumberInput input::-webkit-outer-spin-button,
    .stNumberInput input::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    /* Streamlit UI +, - 버튼 숨기기 */
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] {
        display: none !important;
    }
    
    .stButton button { width: 100%; height: 2.8rem !important; font-size: 1.1rem !important; font-weight: bold !important; }
    .st-expander p { font-size: 1.0rem !important; line-height: 1.4; margin-bottom: 0.3rem; }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 차량 번호 조회 시스템</div>', unsafe_allow_html=True)

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit?gid=1417331015#gid=1417331015"

def reset_search():
    st.session_state["search_val"] = None
    st.session_state["search_submitted"] = False

if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0).fillna("정보 없음")

    # 입력창: 요청하신 안내 문구로 수정 완료
    search_val = st.number_input(
        "차량번호 뒷자리 입력",
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
                
                try:
                    log_entry = f"{now},{search_val},{full_car_no},{name},{car_type},{reason},등록차량\n"
                    with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
                except: pass
        else:
            st.error(f"❌ '{search_num_str}' 등록 정보 없음")
            try:
                log_entry = f"{now},{search_val},정보없음,정보없음,정보없음,정보없음,미등록\n"
                with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
            except: pass

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")