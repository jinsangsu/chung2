
import streamlit as st
import json
import gspread
from google.oauth2.service_account import Credentials

# Streamlit secrets에서 인증 정보 불러오기
service_account_info = json.loads(st.secrets["GOOGLE_KEY_JSON"])
credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(credentials)

# 구글 시트 열기
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ"
worksheet = gc.open_by_url(spreadsheet_url).worksheet("QnA")

# UI 구성
st.title("충청호남본부 매니저 Q&A 입력")

question = st.text_input("설계사 질문을 입력해주세요")
answer = st.text_area("해당 질문에 대한 답변을 입력해주세요")

if st.button("Q&A 등록하기"):
    if question and answer:
        worksheet.append_row([question, answer])
        st.success("질문과 답변이 성공적으로 등록되었습니다!")
    else:
        st.warning("질문과 답변을 모두 입력해주세요.")
