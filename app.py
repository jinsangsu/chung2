
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os

# Google 인증 키 경로 설정
json_key_path = os.path.join(os.path.dirname(__file__), "aesoonkey.json")

# Google Sheets 인증 및 시트 연결
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
sheet = spreadsheet.worksheet("질의응답시트")

# Streamlit UI 구성
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    st.image("aesoon.png", width=100)
with col2:
    st.markdown("<h3 style='margin-top:40px;'>사장님, 무엇이 궁금하신가요?</h3>", unsafe_allow_html=True)

question = st.text_input("질문을 입력해주세요:")

if question:
    records = sheet.get_all_records()
    matched = [r for r in records if question.lower() in r["질문"].lower()]

    if len(matched) == 1:
        st.success(f"답변: {matched[0]['답변']}")
    elif len(matched) > 1:
        st.info("다음 중 어떤 질문을 원하시나요?")
        for i, r in enumerate(matched):
            st.markdown(f"**{i+1}. 질문:** {r['질문']}")
            st.markdown(f"👉 답변: {r['답변']}")
    else:
        st.error("해당 질문에 대한 답변을 찾을 수 없습니다.")
