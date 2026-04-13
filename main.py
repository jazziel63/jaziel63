import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")

# --- 글씨 크기 미세 조정 스타일 설정 ---
st.markdown("""
    <style>
    /* 전체 기본 글씨 크기 표준화 */
    html, body, [class*="css"]  {
        font-size: 0.95rem; 
    }
    .main-title {
        font-size: 1.4rem !important; /* 제목 크기 약간 더 축소 */
        font-weight: bold;
        padding-bottom: 0.8rem;
        color: #31333F;
    }
    .stTextInput label {
        font-size: 1.0rem !important;
        font-weight: bold !important;
    }
    .stTextInput input {
        font-size: 1.2rem !important;
        height: 2.6rem !important;
    }
    .stButton button {
        width: 100%;
        height: 2.8rem !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
    }
    /* 검색 결과 성공 메시지 크기 조절 */
    .stAlert p {
        font-size: 1.0rem !important;
    }
    /* [수정] 결과 박스(Expander) 제목과 내부 글씨 크기 축소 */
    .st-expander {
        border: 1px solid #f0f2f6 !important;
    }
    .st-expander p {
        font-size: 1.0rem !important; /* 결과 텍스트 크기 줄임 */
        line-height: 1.4;
        margin-bottom: 0.3rem;
    }
    .st-expander [data-testid="stExpanderToggleIcon"] + div {
        font-size: 1.05rem !important; /* 리스트 제목 크기 줄임 */
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🚗 차량 번호 조회 시스템</div>', unsafe_allow_html=True)

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit?gid=1417331015#gid=1417331015"

def reset_search():
    st.session_state["car_input"] = "" 
    st.session_state["search_submitted"] = False

if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0).fillna("정보 없음")

    search_input = st.text_input(
        "차량번호 조회", 
        key="car_input",
        max_chars=4,
        placeholder="차량 뒷번호 4자리를 입력하세요",
    ).strip()
    
    if search_input and not search_input.isdigit():
        st.warning("⚠️ 숫자만 입력 가능합니다.")
        search_input = ""

    submit_button = st.button("🔍 조회하기")

    if (submit_button or st.session_state["search_submitted"]) and len(search_input) >= 3:
        st.session_state["search_submitted"] = True
        
        df['검색용번호'] = df['차량번호'].astype(str).str.replace(" ", "")
        results = df[df['검색용번호'].str.contains(search_input)]
        
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
            st.error(f"❌ '{search_input}' 등록 정보 없음")
            try:
                log_entry = f"{now},{search_input},정보없음,정보없음,정보없음,정보없음,미등록\n"
                with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
            except: pass

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 연결 오류: {e}")