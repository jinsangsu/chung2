import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os

# 🖼️ Streamlit UI는 항상 먼저 구성
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("managerbot_character.webp", width=100)
    except:
        st.warning("❗ 캐릭터 이미지를 불러올 수 없습니다.")
with col2:
    st.markdown("""
        <h2 style='margin-top:25px;'>사장님, 안녕하세요!</h2>
        <p>저는 앞으로 사장님들 업무를 도와드리는<br>
        <strong>충청호남본부 매니저봇 ‘애순’</strong>이에요.</p>
        <p>매니저님께 여쭤보시기 전에<br>
        저 애순이한테 먼저 물어봐 주세요!<br>
        제가 아는 건 바로, 친절하게 알려드릴게요!</p>
        <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
        늘 옆에서 든든하게 함께하겠습니다.</p>
        <strong>잘 부탁드려요! 😊</strong>
    """, unsafe_allow_html=True)

st.markdown("### 💬 궁금한 내용을 입력해 주세요")
question = st.text_input("")

# 🔐 Google Sheets 연동 (UI 이후 처리)
sheet = None
try:
    json_key_path = "aesoonkey.json"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# 📥 질문에 따라 검색 실행
if sheet and question:
    try:
        records = sheet.get_all_records()
        q_input = question.lower().replace(" ", "")
        matched = [r for r in records if q_input in r["질문"].lower().replace(" ", "")]

        if len(matched) == 1:
            st.success(f"🧾 애순이의 답변: {matched[0]['답변']}")
        elif len(matched) > 1:
            st.info("🔎 유사한 질문이 여러 개 있습니다:")
            for i, r in enumerate(matched):
                st.markdown(f"**{i+1}. 질문:** {r['질문']}")
                st.markdown(f"👉 답변: {r['답변']}")
        else:
            st.warning("❌ 해당 질문에 대한 답변을 찾을 수 없습니다.")
    except Exception as e:
        st.error(f"❌ 검색 중 오류 발생: {e}")