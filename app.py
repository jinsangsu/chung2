import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
import os

# Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(credentials)

# 구글 시트 불러오기
try:
    sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
    records = sheet.get_all_records()
    st.session_state["sheet_loaded"] = True
except Exception as e:
    st.session_state["sheet_loaded"] = False
    error_message = f"❌ 구글 시트 연결에 실패했습니다. 입력창은 비활성화됩니다.\n\n{e}"
    st.error(error_message)

# 앱 타이틀 및 캐릭터
st.markdown("<h1 style='text-align: center;'>🧑‍💼 애순이 매니저봇</h1>", unsafe_allow_html=True)

# 캐릭터 이미지 출력
col1, col2 = st.columns([1, 4])
with col1:
    try:
        image = Image.open("managerbot_character.png")
        st.image(image, width=120)
    except:
        st.warning("⚠️ 캐릭터 이미지(managerbot_character.png)가 없습니다.")
with col2:
    st.write("")

# 질문 입력창
st.markdown("---")
if not st.session_state["sheet_loaded"]:
    st.text_input("💬 설계사 질문을 입력하세요", placeholder="예: 자동차 이체 방법 알려줘", disabled=True)
else:
    user_question = st.text_input("💬 설계사 질문을 입력하세요", placeholder="예: 자동차 이체 방법 알려줘")
    if user_question:
        matched = [r for r in records if user_question.strip() in r["질문 내용"]]
        if matched:
            st.success("🤖 " + matched[0]["답변 내용"])
        else:
            st.info("🔎 정확히 일치하는 질문이 없습니다. 다시 입력해주세요.")
