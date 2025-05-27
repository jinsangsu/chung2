
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# 📌 페이지 설정
st.set_page_config(page_title="매니저 Q&A 등록", page_icon="📝", layout="centered")

st.title("📋 매니저 질의응답 등록 UI")
st.markdown("질문과 답변을 입력하고 'Google Sheet로 저장' 버튼을 누르세요.")

# ✅ 구글 시트 연동
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('singular-citron-459308-q0-5120c3914ca5.json', scope)
gc = gspread.authorize(credentials)

# 🔗 시트 열기
spreadsheet = gc.open_by_url('https://docs.google.com/spreadsheets/d/1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ/edit#gid=1891969598')
worksheet = spreadsheet.get_worksheet(0)

# 📝 입력 UI
question = st.text_input("질문 내용을 입력하세요:", placeholder="예: 자동차 할부 관련 문의")
answer = st.text_area("답변 내용을 입력하세요:", height=150, placeholder="예: 할부는 12개월, 24개월, 36개월 가능합니다.")
submit = st.button("📤 Google Sheet로 저장")

# ✅ 저장 처리
if submit:
    if question.strip() == "" or answer.strip() == "":
        st.warning("질문과 답변 모두 입력해 주세요.")
    else:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        worksheet.append_row([now, question.strip(), answer.strip()])
        st.success("✅ 성공적으로 저장되었습니다!")
