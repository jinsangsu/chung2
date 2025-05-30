import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import os

# 🔐 Google Sheets 인증
json_key_path = os.path.join(os.path.dirname(__file__), "aesoonkey.json")
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(json_key_path, scopes=scope)
gc = gspread.authorize(credentials)

try:
    sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
    columns = sheet.row_values(1)
    if "질문" not in columns or "답변" not in columns:
        raise Exception("시트에 '질문' 또는 '답변' 열이 없습니다.")
except Exception as e:
    sheet = None
    sheet_error = str(e)

# 🖼️ Streamlit UI
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

if sheet is None:
    st.error(f"🚨 구글 시트를 불러올 수 없습니다: {sheet_error}")
elif question:
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
            st.warning("❌ 해당 질문에 대한 답변을 찾을 수 없습니다. 구글 시트 내 키워드를 다시 확인해 주세요.")
    except Exception as e:
        st.error(f"❌ 검색 중 오류 발생: {e}")