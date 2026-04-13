import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")
st.title("🚗 차량 번호 조회")

def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit?gid=1417331015#gid=1417331015"

# --- 초기화 함수 ---
def reset_search():
    st.session_state["car_input"] = "" 
    st.session_state["search_submitted"] = False

if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0)

    search_input = st.text_input(
        "차량번호 조회", 
        key="car_input",
        max_chars=4,
        placeholder="차량 뒷번호 4자리만 입력하세요",
        help="숫자 4자리만 입력해 주세요."
    ).strip()
    
    submit_button = st.button("🔍 조회하기")

    if (submit_button or st.session_state["search_submitted"]) and len(search_input) == 4:
        st.session_state["search_submitted"] = True
        
        # 검색 로직 (뒷자리 4자리 비교)
        df['뒷자리'] = df['차량번호'].astype(str).str.replace(" ", "").str[-4:]
        results = df[df['뒷자리'] == search_input]
        now = get_now_kst()
        
        if not results.empty:
            st.success(f"### ✅ {len(results)}건의 차량이 검색되었습니다.")
            for i, res in results.iterrows():
                full_car_no = res.get('차량번호', '정보 없음')
                name = res.get('성명', '이름 없음')
                car_type = res.get('차량종류', '정보 없음')
                reason = res.get('제외사유', '없음')
                
                # [명칭 변경] 차주, 차종, 제외사유
                with st.expander(f"📍 {full_car_no} ({name})", expanded=True):
                    st.write(f"**차주:** {name}")
                    st.write(f"**차종:** {car_type}")
                    st.write(f"**제외사유:** {reason}")
                
                # 로그 저장 및 문구 출력
                try:
                    log_entry = f"{now} | 입력: {search_input} | 차주: {name} | 차종: {car_type} | 제외사유: {reason} | 상태: 등록차량\n"
                    with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
                    st.caption("📂 조회 기록이 저장되었습니다.")
                except: pass
        else:
            st.error(f"### ⚠️ '{search_input}'번으로 등록된 차량이 없습니다.")
            try:
                log_entry = f"{now} | 입력: {search_input} | 상태: 미등록\n"
                with open("log.txt", "a", encoding="utf-8") as f: f.write(log_entry)
                st.caption("📂 미등록 차량 조회 기록이 저장되었습니다.")
            except: pass

    if st.session_state["search_submitted"]:
        st.divider()
        st.button("🔄 다시 조회하기", on_click=reset_search)

except Exception as e:
    st.error(f"⚠️ 시스템 연결 오류: {e}")