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

# --- CSS 스타일 (이전과 동일) ---
st.markdown("""
<style>
html, body, #root, .stApp, .streamlit-container {
    height: 100%; margin: 0; padding: 0; display: flex; flex-direction: column;
}
.stApp > header, .stApp > footer { visibility: hidden; height: 0px !important; }
.block-container {
    padding-top: 1rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem;
    flex-grow: 1; display: flex; flex-direction: column; max-width: 700px; margin-left: auto; margin-right: auto;
}
#chat-content-scroll-area {
    flex-grow: 1; overflow-y: auto !important; padding: 10px 0 0 0;
    display: flex; flex-direction: column; justify-content: flex-start; background: #fff;
    height: 420px; min-height: 320px; max-width: 700px;
}
.message-row { display: flex; margin-bottom: 12px; }
.bot-message-row { justify-content: flex-start; }
.bot-bubble {
    background-color: #e0f7fa; color: #333; padding: 8px 14px; border-radius: 12px;
    display: inline-block; max-width: 90%; text-align: left;
}
.intro-bubble {
    background-color: #f6f6fc; color: #252525; box-shadow: 0 2px 6px #eee;
    padding: 16px; border-radius: 12px; text-align: left;
}
.stForm {
    position: sticky; bottom: 0; background-color: white; padding: 10px 20px 8px 20px;
    border-top: 1px solid #e0e0e0; box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
    z-index: 1000; width: 100%; max-width: 700px; margin-left: auto; margin-right: auto;
}
.stTextInput > div > div > input { border-radius: 20px; }
.stButton > button { border-radius: 20px; }
</style>
""", unsafe_allow_html=True)


# --- 이미지, 인사말, 시트 연결 등 함수 (이전과 동일) ---
def get_character_img_base64():
    img_path = "managerbot_character.webp"
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
            return f"data:image/webp;base64,{b64}"
    return None

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

sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    # 파일명을 gspread가 인식하도록 수정
    sh = gc.open("질의응답시트")
    sheet = sh.worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "intro", "content": "", "display_type": "intro"}]

def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# <--- 수정된 부분: handle_question 함수 로직 변경 ---
def handle_question(question_input):
    try:
        # 구글 시트에서 모든 레코드 가져오기
        all_records = sheet.get_all_records() if sheet else []
        q_input = question_input.lower()
        SIMILARITY_THRESHOLD = 0.4
        matched = []

        # 유사도 검사
        for r in all_records:
            # '질문' 키가 있는지 확인
            if '질문' in r and isinstance(r['질문'], str):
                q = r["질문"].lower()
                if q_input in q or get_similarity_score(q_input, q) >= SIMILARITY_THRESHOLD:
                    matched.append(r)
        
        # 사용자 질문을 로그에 추가
        st.session_state.chat_log.append({"role": "user", "content": question_input})
        
        # 매칭된 개수에 따라 분기 처리
        if len(matched) >= 5:
            # 5개 이상이면, 질문 목록만 보여주며 되묻기
            bot_display_type = "clarification_needed"
            bot_answer_content = [r["질문"] for r in matched]
        elif 1 <= len(matched) < 5:
            # 1~4개이면, 직접 답변
            bot_display_type = "direct_answers"
            bot_answer_content = [{"q": r["질문"], "a": r["답변"]} for r in matched]
        else:
            # 매칭 결과가 없으면 LLM 호출
            bot_display_type = "llm_answer"
            try:
                response = requests.post(API_URL, json={"message": question_input}, timeout=30)
                if response.status_code == 200:
                    reply = response.json().get("reply", "답변을 생성할 수 없습니다.")
                else:
                    reply = f"❌ 서버 오류 ({response.status_code})"
            except requests.exceptions.RequestException as e:
                reply = f"❌ 백엔드 API 호출에 실패했습니다: {e}"
            bot_answer_content = reply

        # 봇 응답을 로그에 추가
        st.session_state.chat_log.append({
            "role": "bot", "content": bot_answer_content, "display_type": bot_display_type
        })

    except Exception as e:
        # 전체 프로세스에서 에러 발생 시
        st.session_state.chat_log.append({
            "role": "bot", "content": f"❌ 오류 발생: {e}", "display_type": "llm_answer"
        })

# <--- 수정된 부분: display_chat_html_content 함수 로직 변경 ---
def display_chat_html_content():
    chat_html_content = ""
    for entry in st.session_state.chat_log:
        role = entry.get("role")
        display_type = entry.get("display_type")
        content = entry.get("content")

        if role == "intro":
            chat_html_content += f'<div class="message-row bot-message-row"><div class="intro-bubble">{get_intro_html()}</div></div>'
        
        elif role == "user":
            user_question = content.replace("\n", "<br>")
            chat_html_content += (
                f'<div class="message-row" style="display:flex; justify-content:flex-end;">'
                f'<div style="background:#dcf8c6; color:#111; font-weight:700; padding:8px 14px; border-radius:12px; display:inline-block; max-width:80%;">'
                f'{user_question}'
                '</div></div>'
            )

        elif role == "bot":
            chat_html_content += '<div class="message-row bot-message-row"><div class="bot-bubble">'
            
            if display_type == "clarification_needed":
                # 5개 이상 매칭 시 되묻는 UI
                chat_html_content += "<p><strong>질문이 너무 광범위합니다.</strong><br>아래 목록에서 궁금하신 질문과 가장 유사한 것을 다시 입력하시거나, 질문을 더 구체적으로 작성해주세요.</p><hr style='margin: 8px 0;'>"
                for i, q_text in enumerate(content):
                    chat_html_content += f"<p style='margin: 5px 0;'>{i+1}. {q_text.replace('\n', '<br>')}</p>"

            elif display_type == "direct_answers":
                # 1~4개 매칭 시 직접 답변하는 UI
                for i, pair in enumerate(content):
                    chat_html_content += f"""
                    <div style="margin-bottom: 10px;">
                        <p style="margin-bottom: 5px;"><strong>질문:</strong> {pair['q'].replace('\n', '<br>')}</p>
                        <p>👉 <strong>답변:</strong> {pair['a'].replace('\n', '<br>')}</p>
                    </div>
                    """
            elif display_type == "llm_answer":
                # LLM 답변 UI
                chat_html_content += f"<p>🧾 <strong>답변:</strong><br>{content.replace('\n', '<br>')}</p>"
                
            chat_html_content += '</div></div>'

    # 스크롤 스크립트
    scroll_script = """
    <script>
    setTimeout(function() {
        var anchor = document.getElementById("chat-scroll-anchor");
        if (anchor) { anchor.scrollIntoView({ behavior: "auto", block: "end" }); }
    }, 0);
    </script>
    """
    return f'<div id="chat-content-scroll-area">{chat_html_content}<div id="chat-scroll-anchor"></div></div>{scroll_script}'

# --- UI 렌더링 및 입력 폼 (이전과 동일) ---
components.html(display_chat_html_content(), height=520, scrolling=True)

with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box", placeholder="여기에 질문을 입력하세요...")
    if st.form_submit_button("질문하기"):
        if question_input:
            handle_question(question_input)
            st.rerun()