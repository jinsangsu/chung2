import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import requests
import base64
import os

API_URL = "https://chung2.fly.dev/chat"

st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

# --- CSS
st.markdown("""
<style>
    html, body, #root, .stApp, .streamlit-container {
        height: 100%;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
    }
    .stApp > header, .stApp > footer {
        visibility: hidden;
        height: 0px !important;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
    }
    /* 채팅 메시지 영역 */
    #chat-content-scroll-area {
        flex-grow: 1;
        overflow-y: auto !important;   /* 항상 스크롤바 표시 */
        padding: 10px 0 0 0;
        scroll-behavior: smooth;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        background: #fff;
        height: 420px;
        min-height: 320px;
        max-height: 520px;
    }
    .message-row {
        display: flex;
        margin-bottom: 12px;
        width: 100%;
    }
    .user-message-row { justify-content: flex-end; }
    .bot-message-row, .intro-message-row { justify-content: flex-start; }
    .message-bubble {
        max-width: 80%;
        padding: 10px 14px;
        border-radius: 15px;
        word-wrap: break-word;
        font-size: 1.04em;
    }
    .user-bubble {
        background-color: #dcf8c6;
        color: #111;
        font-weight: 700;
        text-align: right;
    }
    .bot-bubble {
        background-color: #e0f7fa;
        color: #333;
        font-weight: 400;
        text-align: left;
    }
    .intro-bubble {
        background-color: #f6f6fc;
        color: #252525;
        box-shadow: 0 2px 6px #eee;
        font-weight: 400;
        text-align: left;
    }
    /* 유사 질문 */
    .chat-multi-item {
        margin-left: 25px;
        font-size: 0.98em;
        margin-bottom: 5px;
    }
    /* 입력 폼 고정 */
    .stForm {
        position: sticky;
        bottom: 0;
        background-color: white;
        padding: 10px 20px 8px 20px;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
        z-index: 1000;
        width: 100%;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding-right: 40px;
    }
    .stButton > button {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 캐릭터 이미지를 base64로 변환해서 인라인으로 사용(배포환경 호환용)
def get_character_img_base64():
    img_path = "managerbot_character.webp"
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
            return f"data:image/webp;base64,{b64}"
    else:
        return None

# --- 인사말(캐릭터+소개) html
def get_intro_html():
    char_img = get_character_img_base64()
    img_tag = f'<img src="{char_img}" width="75" style="margin-right:17px; border-radius:16px; border:1px solid #eee;">' if char_img else ''
    return f"""
    <div style="display: flex; align-items: flex-start; margin-bottom:18px;">
        {img_tag}
        <div>
            <h2 style='margin:0 0 8px 0;font-weight:900;'>사장님, 안녕하세요!</h2>
            <p>저는 앞으로 사장님들 업무를 도와드리는<br>
            <strong>충청호남본부 매니저봇 ‘애순’</strong>이에요.</p>
            <p>매니저님께 여쭤보시기 전에<br>
            저 애순이한테 먼저 물어봐 주세요!<br>
            제가 아는 건 바로, 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
            늘 옆에서 든든하게 함께하겠습니다.</p>
            <strong>잘 부탁드려요! 😊</strong>
        </div>
    </div>
    """

# --- 구글 시트 연결
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# --- 세션 상태: chat_log
if "chat_log" not in st.session_state:
    # 최초 인사말 메시지를 가장 위에 push
    st.session_state.chat_log = [
        {"role": "intro", "content": "", "display_type": "intro"}
    ]
if "scroll_to_bottom_flag" not in st.session_state:
    st.session_state.scroll_to_bottom_flag = False

# --- 유사도 계산
def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# --- 질문 처리
def handle_question(question_input):
    try:
        records = sheet.get_all_records()
        q_input = question_input.lower()
        SIMILARITY_THRESHOLD = 0.4
        matched = []
        for r in records:
            q = r["질문"].lower()
            if q_input in q or get_similarity_score(q_input, q) >= SIMILARITY_THRESHOLD:
                matched.append(r)

        # 질문 추가
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        # 답변 추가
        if len(matched) == 1:
            bot_answer_content = matched[0]["답변"]
            bot_display_type = "single_answer"
        elif len(matched) > 1:
            bot_answer_content = [{"q": r["질문"], "a": r["답변"]} for r in matched]
            bot_display_type = "multi_answer"
        else:
            try:
                response = requests.post(API_URL, json={"message": question_input})
                if response.status_code == 200:
                    data = response.json()
                    reply = data.get("reply", "❌ 응답이 비어 있습니다.")
                else:
                    reply = f"❌ 서버 오류 (Status {response.status_code})"
                bot_answer_content = reply
            except Exception as e:
                bot_answer_content = f"❌ 백엔드 응답 실패: {e}"
            bot_display_type = "single_answer"

        st.session_state.chat_log.append({
            "role": "bot",
            "content": bot_answer_content,
            "display_type": b_
