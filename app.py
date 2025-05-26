
import streamlit as st
import requests
from PIL import Image

# 앱 설정 및 스타일
st.set_page_config(page_title="애순이 챗봇", page_icon="💛", layout="centered")
st.markdown("<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True)

# 상단 캐릭터 + 문구
col1, col2 = st.columns([1, 5])
with col1:
    st.image("managerbot_character.webp", width=130)
with col2:
    st.markdown("#### **사장님, 안녕하세요!**")
    st.markdown("""저는 앞으로 사장님들 업무를 도와드리는  
**충청호남본부 매니저봇 ‘애순’**이에요.

매니저님께 여쭤보시기 전에  
저 애순이한테 먼저 물어봐 주세요!  
제가 아는 건 바로, 친절하게 알려드릴게요!

사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록  
늘 옆에서 든든하게 함께하겠습니다.  
**잘 부탁드려요! 😊**""")

st.markdown("---")

# GPT 서버 주소
GPT_SERVER_URL = "https://chung2.fly.dev/chat"

# 대화 저장
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 채팅 표시
for q, a in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        st.markdown(a)

# 고정 입력창
if prompt := st.chat_input("궁금한 내용을 입력해 주세요"):
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.spinner("애순이가 답변을 준비 중입니다..."):
            response = requests.post(GPT_SERVER_URL, json={"message": prompt})
            if response.status_code == 200:
                reply = response.json().get("reply", "애순이가 이해하지 못했어요.")
            else:
                reply = "애순이 응답을 받지 못했어요. 서버 상태를 확인해 주세요."
    except Exception as e:
        reply = f"애순이 처리 중 오류 발생: {e}"

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat_history.append((prompt, reply))
