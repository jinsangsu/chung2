import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os

# 현재 실행 경로 기준 service_account 키 파일 위치 설정
json_key_path = os.path.join(os.path.dirname(__file__), "aesoonkey.json")

# Google Sheets API 범위 설정
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
gc = gspread.authorize(credentials)

# 시트 열기
spreadsheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
sheet = spreadsheet.worksheet("질의응답시트")

# Streamlit UI
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

st.title("💬 애순이 설계사 Q&A")
st.markdown("설계사님이 자주 묻는 질문과 답변을 확인하거나, 새로운 질문을 입력해보세요.")

question = st.text_input("질문을 입력해주세요:")

if st.button("질문하기"):
    if question.strip() == "":
        st.warning("질문을 입력해주세요.")
    else:
        # 시트에서 질문 열 검색
        records = sheet.get_all_records()
        matched = [r for r in records if question.strip() in r["질문"]]

        if len(matched) == 1:
            st.success(f"답변: {matched[0]['답변']}")
        elif len(matched) > 1:
            st.info("해당 질문과 유사한 질문이 여러 개 있습니다. 아래에서 선택해주세요.")
            for i, r in enumerate(matched):
                st.markdown(f"**{i+1}. 질문:** {r['질문']}")
                st.markdown(f"👉 답변: {r['답변']}")
        else:
            st.error("해당 질문에 대한 답변을 찾을 수 없습니다.")