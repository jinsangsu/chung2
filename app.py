
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# 경로 설정
json_key_path = os.path.join(os.getcwd(), 'singular-citron-459308-q0-5120c3914ca5.json')
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 인증 및 구글시트 연동
credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")

# 데이터 로드
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Streamlit UI
st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="centered")
st.title("💛 애순이 매니저봇")
st.markdown("사장님, 궁금한 내용을 입력해 주세요. 제가 도와드릴게요!")

# 사용자 질문 입력
question = st.text_input("질문을 입력하세요:")

if question:
    matched = df[df["질문 내용"].str.contains(question, case=False, na=False)]

    if len(matched) == 1:
        st.success(matched["답변 내용"].values[0])
    elif len(matched) > 1:
        st.info("여러 개의 유사한 질문이 있습니다. 아래에서 선택해 주세요:")
        selected = st.selectbox("유사 질문 목록", matched["질문 내용"].values)
        if selected:
            st.success(matched[matched["질문 내용"] == selected]["답변 내용"].values[0])
    else:
        st.warning("죄송해요. 해당 질문에 대한 답변을 찾을 수 없어요.")
