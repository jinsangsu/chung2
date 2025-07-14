import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import requests

API_URL = "https://chung2.fly.dev/chat"

st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

# ---- CSS ----
st.markdown("""
<style>
.stForm {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 100;
    background: white; max-width:700px; margin:0 auto;
    border-top:1px solid #e0e0e0; box-shadow:0 -2px 5px rgba(0,0,0,0.05);
}
.block-container { padding-bottom: 125px !important; }
.message-row { display:flex; margin-bottom:10px; width:100%;}
.user-message-row { justify-content: flex-end;}
.bot-message-row { justify-content: flex-start;}
.message-bubble { max-width:70%; padding:8px 12px; border-radius:15px;}
.user-bubble { background-color:#dcf8c6; color:#333;}
.bot-bubble { background-color:#e0f7fa; color:#333;}
.char-row { display: flex; align-items: flex-start; margin-bottom: 12px;}
.char-img { margin-right: 20px;}
.char-txt { font-size:1rem;}
@media (max-width: 600px) {
  .block-container { padding-bottom: 160px !important; }
  .stForm { max-width: 100vw; }
}
</style>
""", unsafe_allow_html=True)

# ---- 캐릭터 소개(항상 상단) ----
st.markdown("""
<div class="char-row">
    <div class="char-img">
        <img src="https://raw.githubusercontent.com/licjssj777/kb-managerbot-character/main/managerbot_character.webp" width="82">
    </div>
    <div class="char-txt">
        <b style="font-size:1.2em;">사장님, 안녕하세요!</b><br>
        저는 앞으로 사장님들 업무를 도와드리는<br>
        <b>충청호남본부 매니저봇 ‘애순’</b>이에요.<br>
        <span style="color:#8db600">매니저님께 여쭤보시기 전에<br>
        저 애순이한테 먼저 물어봐 주세요!<br>
        제가 아는 건 바로, 친절하게 알려드릴게요!</span><br>
        사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
        늘 옆에서 든든하게 함께하겠습니다.<br>
        <b>잘 부탁드려요! 😊</b>
    </div>
</div>
""", unsafe_allow_html=True)

# ---- 구글 시트 연결 ----
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.warning("❌ 구글 시트 연동 실패")

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def handle_question(q_input):
    matched = []
    try:
        for r in sheet.get_all_records():
            if q_input in r["질문"].lower() or get_similarity_score(q_input, r["질문"].lower()) >= 0.4:
                matched.append(r)
    except:
        pass

    st.session_state.chat_log.append({"role": "user", "content": q_input})
    if matched:
        for r in matched:
            st.session_state.chat_log.append({"role": "bot", "content": r["답변"]})
    else:
        try:
            res = requests.post(API_URL, json={"message": q_input})
            reply = res.json().get("reply", "❌ 응답 없음")
        except:
            reply = "❌ 서버 응답 실패"
        st.session_state.chat_log.append({"role": "bot", "content": reply})

def render_chat_html():
    html = ""
    for msg in st.session_state.chat_log:
        role = msg["role"]
        bubble_class = "user-bubble" if role == "user" else "bot-bubble"
        row_class = "user-message-row" if role == "user" else "bot-message-row"
        html += f'<div class="message-row {row_class}"><div class="message-bubble {bubble_class}">{msg["content"]}</div></div>'
    return f"<div style='height:calc(100vh - 240px);overflow-y:auto;padding:10px'>{html}</div>"

components.html(render_chat_html(), height=500, scrolling=True)

# ---- 하단 입력 폼 ----
with st.form("input_form", clear_on_submit=True):
    q = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    if st.form_submit_button("질문하기") and q:
        handle_question(q)
        st.rerun()