
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 구글 시트 연동
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(credentials)

# 본부장님의 Google Sheet 정보
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
worksheet = sheet.worksheet("QnA")

st.title("충청호남본부 매니저 Q&A 입력")

question = st.text_input("설계사 질문을 입력해주세요")
answer = st.text_area("해당 질문에 대한 답변을 입력해주세요")

if st.button("Q&A 등록하기"):
    if question and answer:
        worksheet.append_row([question, answer])
        st.success("질문과 답변이 성공적으로 등록되었습니다!")
    else:
        st.warning("질문과 답변을 모두 입력해주세요.")
