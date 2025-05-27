
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
import pandas as pd
import json

# 페이지 설정
st.set_page_config(page_title="매니저 Q&A 등록", layout="centered")

st.title("💬 매니저 Q&A 입력")
st.markdown("매니저님, 설계사분들이 자주 묻는 질문과 답변을 여기에 입력해주세요.")

# 구글 서비스 계정 인증
service_account_info = json.loads(st.secrets["GOOGLE_KEY_JSON"])
credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(credentials)

# 시트 열기
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ/edit#gid=0"
spreadsheet = gc.open_by_url(spreadsheet_url)
worksheet = spreadsheet.worksheet("질의응답시트")

# 입력 폼
question = st.text_input("질문 내용", placeholder="예: 자동이체는 어떻게 하나요?")
answer = st.text_area("답변 내용", placeholder="예: 고객 앱에서 설정 가능하며, 제안서 화면 우측 메뉴에서도 가능합니다.")

if st.button("등록하기"):
    if question.strip() and answer.strip():
        worksheet.append_row([question, answer])
        st.success("질문과 답변이 성공적으로 등록되었습니다.")
    else:
        st.error("질문과 답변을 모두 입력해주세요.")

# Q&A 리스트 확인
if st.checkbox("🗂 등록된 Q&A 보기"):
    records = worksheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        st.dataframe(df)
    else:
        st.info("등록된 Q&A가 없습니다.")
