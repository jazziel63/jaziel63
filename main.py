import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone
import os

# 웹페이지 설정
st.set_page_config(page_title="학교 차량 조회 시스템", layout="centered")
st.title("🚗 학교 차량 조회 시스템")

# 한국 시간 설정
def get_now_kst():
    kst = timezone(timedelta(hours=9))
    return datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')

# 구글 시트 주소 (보내주신 원본 gid 유지)
URL = "https://docs.google.com/spreadsheets/d/1fXf_WsaVgJJL8kr_22mRLhTrnYMZXm_HfAW9Y97GoMI/edit?gid=1417331015#gid=1417331015"

# --- 세션 상태 관리 ---
if "search_submitted" not in st.session_state:
    st.session_state["search_submitted"] = False

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL, ttl=0)

    # 1. 입력창
    search_input = st.text_input("조회할 차량번호를 입력하세요", key="car_input").replace(" ", "")
    submit_button = st.button("🔍 검색")

    # 2. 검색 및 결과 출력
    if (submit_button or st.session_state["search_submitted"]) and search_input:
        st.session_state["search_submitted"] = True
        
        result = df[df['차량번호'].astype(str).str.replace(" ", "") == search_input]
        now = get_now_kst()
        
        if not result.empty:
            res = result.iloc[0]
            name = res.get('성명', '이름 없음')
            car_type = res.get('차량종류', '정보 없음') # 차량종류 가져오기
            reason = res.get('제외사유', '없음')
            
            st.success(f"### ✅ 등록 차량입니다")
            st.info(f"**성함:** {name}  \n**차량종류:** {car_type}  \n**사유:** {reason}")
            status = "등록차량"
        else:
            name = "미등록"
            car_type = "-" # 미등록 차량은 종류 알 수 없음
            status = "미등록"
            st.error("### ⚠️ 미등록 차량입니다")

        # 3. 로컬 메모장(log.txt)에 차량종류 포함하여 저장
        try:
            # 로그 형식에 '차량종류'를 추가했습니다.
            log_entry = f"{now} | 차량번호: {search_input} | 성명: {name} | 차량종류: {car_type} | 상태: {status}\n"
            with open("log.txt", "a", encoding="utf-8") as f:
                f.write(log_entry)
            st.caption("📂 조회 기록이 저장되었습니다.")
        except Exception as e:
            st.caption(f"⚠️ 기록 저장 실패 (로컬): {e}")

    # 4. 초기화 버튼
    if st.session_state["search_submitted"]:
        st.divider()
        if st.button("🔄 다시 조회하기 (초기화)"):
            if "car_input" in st.session_state:
                del st.session_state["car_input"]
            st.session_state["search_submitted"] = False
            st.rerun()

except Exception as e:
    st.error(f"⚠️ 시스템 연결 오류: {e}")