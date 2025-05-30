
import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
import os

# 페이지 설정
st.set_page_config(page_title="애순이봇", layout="wide")

st.markdown("<h1 style='text-align: center;'>👩‍💼 애순이 매니저봇</h1>", unsafe_allow_html=True)
st.markdown("---")

# 🔐 GCP 서비스 키 위치
json_key_path = os.path.join(os.path.dirname(__file__), 'aesoonkey.json')
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 🛡 예외 방지: 인증 + 시트 연결
try:
    credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
    data = sheet.get_all_records()
    st.success("✅ 구글 시트 연동 완료")
except Exception as e:
    st.error("❌ 구글 시트 연결에 실패했습니다. 입력창은 비활성화됩니다.")
    data = []  # 빈 리스트로 설정

# 🔄 질문 입력 UI
question = st.text_input("💬 설계사 질문을 입력하세요", placeholder="예: 자동이체 방법 알려줘")

# 🔍 검색 및 응답
if question and data:
    matched_answers = [row['답변'] for row in data if row['질문'] in question]
    if matched_answers:
        for answer in matched_answers:
            st.info(f"🟢 {answer}")
    else:
        st.warning("해당 질문에 대한 답변을 찾을 수 없습니다.")
elif question and not data:
    st.warning("⚠️ 시트 데이터를 불러오지 못해 답변할 수 없습니다.")
