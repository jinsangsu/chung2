
import streamlit as st
import requests

st.set_page_config(page_title="애순이 매니저봇", page_icon="🤖")

# 캐릭터 이미지 출력
st.image("managerbot_character.webp", width=150)

# 웰컴 메시지 표시
st.markdown("## 사장님, 안녕하세요!")
st.markdown(
    """
    저는 앞으로 사장님들 업무를 도와드리는  
    **충청호남본부 매니저봇 ‘애순’**이에요.  

    매니저님께 여쭤보시기 전에  
    저 애순이한테 먼저 물어봐 주세요!  
    제가 아는 건 바로, 친절하게 알려드릴게요!  

    사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록  
    늘 옆에서 든든하게 함께하겠습니다.  

    **잘 부탁드려요! 😊**
    """
)

# 세션 상태 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 질문 입력창
user_input = st.chat_input("궁금한 내용을 입력해 주세요")

# 입력값 처리
if user_input:
    payload = {"message": user_input, "user": "jinipark77"}
    try:
        response = requests.post("https://chung2.fly.dev/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data.get("reply", "⚠️ 애순이가 아직 답변을 준비 중이에요.")
    except Exception as e:
        answer = f"❌ 애순이 응답을 받지 못했어요. 서버 상태를 확인해 주세요."

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": answer})

# 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
