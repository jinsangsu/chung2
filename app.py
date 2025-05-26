
import streamlit as st
import requests
from PIL import Image

# 애순이 캐릭터 이미지 (같은 폴더에 이미지 파일 필요)
st.set_page_config(page_title="애순이 챗봇", page_icon="💛")
st.markdown("<h1 style='text-align: center;'>사장님, 안녕하세요! 🤗</h1>", unsafe_allow_html=True)

# 입력창
user_input = st.text_input("궁금한 내용을 입력해 주세요", placeholder="예: 자동차 할인특약에는 어떤 것이 있나요?", key="input")

# GPT 응답 서버 주소
GPT_SERVER_URL = "https://main-sparkling-water-7662.fly.dev/chat"

if user_input:
    try:
        with st.spinner("애순이가 답변을 준비 중입니다..."):
            response = requests.post(GPT_SERVER_URL, json={"message": user_input})
            if response.status_code == 200:
                reply = response.json().get("reply", "")
                st.success(reply)
            else:
                st.error("애순이 응답을 받지 못했어요. 다시 시도해 주세요.")
    except Exception as e:
        st.error(f"오류 발생: {e}")
