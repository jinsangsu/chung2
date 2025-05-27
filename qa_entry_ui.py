
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 🔐 인증 설정
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(
    "singular-citron-459308-q0-5120c3914ca5.json", scopes=scope
)
gc = gspread.authorize(credentials)

# 📄 구글시트 열기
sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")

# 🖼️ UI 구성
st.set_page_config(page_title="매니저 질의응답 등록 UI", layout="centered", page_icon="📝")
st.title("📝 매니저 질의응답 등록 UI")
st.markdown("질문과 답변을 입력하고 'Google Sheet로 저장' 버튼을 누르세요.")

question = st.text_input("질문을 입력하세요:")
answer = st.text_area("답변을 입력하세요:")

if st.button("Google Sheet로 저장"):
    try:
        if question.strip() == "" or answer.strip() == "":
            st.warning("질문과 답변을 모두 입력해 주세요.")
        else:
            sheet.append_row([question, answer])
            st.success("✅ Google Sheet에 성공적으로 저장되었습니다.")
    except Exception as e:
        st.error(f"❌ 저장 실패: {e}")
