import streamlit as st
import requests

# 📌 FastAPI 서버 주소 설정
API_URL = "http://localhost:8000/chat"  # 필요 시 fly.io 주소로 교체 가능

# 🖼️ 페이지 구성
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

# 💬 Welcoming 메시지 + 캐릭터
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

# 📥 질문 입력
st.markdown("### 💬 궁금한 내용을 입력해 주세요")
question = st.text_input("")

# 📤 FastAPI에 요청 전송
if question:
    try:
        response = requests.post(API_URL, json={"message": question}, timeout=5)
        if response.status_code == 200:
            reply = response.json().get("reply", "")
            st.success(f"🧾 애순이의 답변: {reply}")
        else:
            st.error("❌ 애순이 응답을 받지 못했어요. 서버 상태를 확인해 주세요.")
    except Exception as e:
        st.error(f"🚨 서버 통신 오류: {e}")