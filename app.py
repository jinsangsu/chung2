
import streamlit as st
import requests
from PIL import Image

# 앱 설정
st.set_page_config(page_title="애순이 챗봇", page_icon="💛")

# 상단 영역 구성 (캐릭터 왼쪽 + 인사말 오른쪽)
st.markdown("<style>div.block-container{padding-top:1rem;}</style>", unsafe_allow_html=True)
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

# 질문 입력창
user_input = st.text_input("궁금한 내용을 입력해 주세요", placeholder="예: 자동차 할인특약에는 어떤 것이 있나요?")

# GPT 응답 서버 주소
GPT_SERVER_URL = "https://chung2.fly.dev/chat"

if user_input:
    try:
        with st.spinner("애순이가 답변을 준비 중입니다..."):
            response = requests.post(GPT_SERVER_URL, json={"message": user_input})
            if response.status_code == 200:
                reply = response.json().get("reply", "")
                if reply:
                    st.success(reply)
                else:
                    st.warning("애순이가 적절한 답을 찾지 못했어요 😥")
            else:
                st.error("애순이 응답을 받지 못했어요. 서버 상태를 확인해 주세요.")
    except Exception as e:
        st.error(f"애순이 처리 중 오류 발생: {e}")
