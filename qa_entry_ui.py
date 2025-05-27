import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="매니저 질의응답 등록 UI", page_icon="📝")

st.title("📝 매니저 질의응답 등록 UI")
st.markdown("질문과 답변을 입력하고 'Google Sheet로 저장' 버튼을 누르세요.")

# 질문 및 답변 입력
question = st.text_input("질문을 입력하세요:")
answer = st.text_area("답변을 입력하세요:")

# 구글 서비스 계정 인증
SERVICE_ACCOUNT_FILE = 'singular-citron-459308-q0-5120c3914ca5.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# 구글 시트 연결
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key('1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ')  # 안정적 방식
worksheet = spreadsheet.sheet1

# 저장 버튼
if st.button("Google Sheet로 저장"):
    try:
        worksheet.append_row([question, answer])
        st.success("✅ Google Sheet에 저장되었습니다!")
    except Exception as e:
        st.error(f"❌ 저장 중 오류 발생: {e}")