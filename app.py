
import streamlit as st
import requests

st.set_page_config(page_title="애순이 매니저봇", page_icon="🤖")

st.markdown("## 사장님, 안녕하세요!")
st.markdown("저는 앞으로 사장님들 업무를 도와드리는 **충청호남본부 매니저봇 ‘애순’**이에요.")
st.markdown("매니저님께 여쭤보시기 전에 저 애순이한테 먼저 물어봐 주세요!\n제가 아는 건 바로, 친절하게 알려드릴게요!")

# 기본 세션 상태 초기화
if 'messages' not in st.session_state:
    st.session_state.messages = []

# 사용자 질문 입력창
user_input = st.chat_input("궁금한 내용을 입력해 주세요")

if user_input:
    payload = {"message": user_input, "user": "jinipark77"}
    try:
        response = requests.post("https://chung2.fly.dev/chat", json=payload)
        response.raise_for_status()  # HTTP 오류 확인
        data = response.json()
        answer = data.get("reply", "⚠️ 애순이가 아직 답변을 준비 중이에요.")
    except Exception as e:
        answer = f"❌ 서버 응답 오류: {e}"

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": answer})

# 채팅 메시지 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
