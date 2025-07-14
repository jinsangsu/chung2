import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import requests
import re

st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

st.markdown("""
<style>
.block-container { padding-bottom: 115px !important; }
.chat-wrap { max-width: 700px; margin:0 auto; }
.msg-row { display:flex; align-items: flex-end; margin-bottom: 13px; }
.msg-user { justify-content: flex-end; }
.msg-bot { justify-content: flex-start; }
.msg-bubble {
    max-width: 67%%;
    padding: 11px 17px;
    border-radius: 18px;
    font-size: 1.08em;
    box-shadow: 0 1px 4px rgba(180,180,180,0.07);
    line-height: 1.6;
    white-space: pre-line;
    word-break: break-word;
}
.bubble-user { background: #dcf8c6; color: #222; border-bottom-right-radius: 7px;}
.bubble-bot { background: #f5f7fa; color: #222; border-bottom-left-radius: 7px;}
.bot-profile { width:38px; height:38px; margin-right:8px; border-radius:50%; object-fit:cover;}
@media (max-width: 600px) {
  .block-container { padding-bottom: 150px !important; }
  .chat-wrap { max-width:100vw; }
  .msg-bubble { font-size:1em; }
}
</style>
""", unsafe_allow_html=True)

# 상단 캐릭터 소개
st.markdown("""
<div class="chat-wrap" style="display:flex;align-items:flex-start;margin-bottom:18px;">
    <img src="https://raw.githubusercontent.com/licjssj777/kb-managerbot-character/main/managerbot_character.webp" width="58" style="margin-right:18px;">
    <div style="font-size:1.07em;">
        <b style="font-size:1.15em;">사장님, 안녕하세요!</b><br>
        저는 앞으로 사장님들 업무를 도와드리는<br>
        <b>충청호남본부 매니저봇 ‘애순’</b>이에요.<br>
        <span style="color:#8db600">매니저님께 여쭤보시기 전에 저 애순이한테 먼저 물어봐 주세요!<br>
        제가 아는 건 바로, 친절하게 알려드릴게요!</span><br>
        사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
        늘 옆에서 든든하게 함께하겠습니다.<br>
        <b>잘 부탁드려요! 😊</b>
    </div>
</div>
""", unsafe_allow_html=True)

# 구글 시트 연결 등 이하 동일...
# (handle_question, clean_text, etc...)

# render_chat_html 함수 내에서 한 줄씩 번갈아
def render_chat_html():
    html = '<div class="chat-wrap">'
    bot_profile_url = "https://raw.githubusercontent.com/licjssj777/kb-managerbot-character/main/managerbot_character.webp"
    for msg in st.session_state.chat_log:
        content = re.sub(r"<[^>]+>", "", str(msg["content"])) # 모든 태그 제거
        if msg["role"] == "user":
            html += f"""
            <div class="msg-row msg-user">
                <div class="msg-bubble bubble-user">{content}</div>
            </div>"""
        else:
            html += f"""
            <div class="msg-row msg-bot">
                <img src="{bot_profile_url}" class="bot-profile" alt="bot">
                <div class="msg-bubble bubble-bot">{content}</div>
            </div>"""
    html += "</div>"
    return html

components.html(render_chat_html(), height=600, scrolling=True)

with st.form("input_form", clear_on_submit=True):
    q = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    if st.form_submit_button("질문하기") and q:
        handle_question(q)
        st.rerun()
