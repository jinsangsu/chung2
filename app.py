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

# --- CSS: 사용자/봇 스타일을 명확히 분리하여 재작성 ---
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
    flex-grow: 1; overflow-y: auto !important; padding: 10px 0 0 0; scroll-behavior: smooth;
    display: flex; flex-direction: column; justify-content: flex-start; background: #fff;
    height: 420px; min-height: 320px; max-width: 700px;
}
/* <--- 수정된 부분 시작 --- */
.user-message-row, .bot-message-row {
    display: flex;
    margin-bottom: 12px;
}
.user-message-row {
    justify-content: flex-end; /* 사용자 질문은 오른쪽 정렬 */
}
.bot-message-row {
    justify-content: flex-start; /* 봇 답변은 왼쪽 정렬 */
}
/* <--- 수정된 부분 끝 --- */
.user-bubble {
    background-color: #dcf8c6; color: #111; font-weight: 700 !important;
    text-align: right !important; padding: 8px 14px; border-radius: 12px;
    display: inline-block; max-width: 80%;
}
.bot-bubble {
    background-color: #e0f7fa; color: #333; font-weight: 400; text-align: left;
    padding: 8px 14px; border-radius: 12px; display: inline-block; max-width: 90%;
}
.intro-bubble {
    background-color: #f6f6fc; color: #252525; box-shadow: 0 2px 6px #eee;
    font-weight: 400; text-align: left; padding: 16px; border-radius: 12px;
}
.chat-multi-item { margin-left: 25px; font-size: 0.98em; margin-bottom: 5px; }
.stForm {
    position: sticky; bottom: 0; background-color: white; padding: 10px 20px 8px 20px;
    border-top: 1px solid #e0e0e0; box-shadow: 0 -2px 8px rgba(0,0,0,0.06);
    z-index: 1000; width: 100%; max-width: 700px; margin-left: auto; margin-right: auto;
}
.stTextInput > div > div > input { border-radius: 20px; padding-right: 40px; }
.stButton > button { border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 캐릭터 이미지, 인사말 HTML (이전과 동일) ---
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

# --- 구글 시트 연결 (이전과 동일) ---
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# --- 세션 상태 초기화 (이전과 동일) ---
if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "intro", "content": "", "display_type": "intro"}]
if "scroll_to_bottom_flag" not in st.session_state:
    st.session_state.scroll_to_bottom_flag = False

# --- 유사도 계산 (이전과 동일) ---
def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# --- 질문 처리 (이전과 동일) ---
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

        st.session_state.chat_log.append({
            "role": "user", "content": question_input, "display_type": "question"
        })

        if len(matched) == 1:
            bot_answer_content = {"q": matched[0]["질문"], "a": matched[0]["답변"]}
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
                bot_display_type = "llm_answer"
            except Exception as e:
                bot_answer_content = f"❌ 백엔드 응답 실패: {e}"
                bot_display_type = "llm_answer"

        st.session_state.chat_log.append({
            "role": "bot", "content": bot_answer_content, "display_type": bot_display_type
        })
        st.session_state.scroll_to_bottom_flag = True

    except Exception as e:
        st.session_state.chat_log.append({
            "role": "bot", "content": f"❌ 오류 발생: {e}", "display_type": "llm_answer"
        })
        st.session_state.scroll_to_bottom_flag = True

# --- 채팅 대화방 전체 HTML 렌더 (로직 수정) ---
def display_chat_html_content():
    chat_html_content = ""
    for entry in st.session_state.chat_log:
        if entry["role"] == "intro":
            # <--- 수정된 부분: bot-message-row 클래스 사용
            chat_html_content += f'<div class="bot-message-row"><div class="intro-bubble">{get_intro_html()}</div></div>'
        elif entry["role"] == "user":
            user_question = entry["content"].replace("\n", "<br>")
            # <--- 수정된 부분: user-message-row 클래스만 사용
            chat_html_content += f'<div class="user-message-row"><div class="user-bubble">{user_question}</div></div>'
        elif entry["role"] == "bot":
            # <--- 수정된 부분: bot-message-row 클래스만 사용
            chat_html_content += '<div class="bot-message-row"><div class="bot-bubble">'
            
            display_type = entry.get("display_type")
            if display_type == "single_answer":
                q = entry['content']['q'].replace('\n', '<br>')
                a = entry['content']['a'].replace('\n', '<br>')
                chat_html_content += f"""
                <p style="margin-bottom: 8px;"><strong>질문:</strong> {q}</p>
                <p>👉 <strong>답변:</strong> {a}</p>
                """
            elif display_type == "multi_answer":
                chat_html_content += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
                for i, pair in enumerate(entry["content"]):
                    q = pair['q'].replace('\n', '<br>')
                    a = pair['a'].replace('\n', '<br>')
                    chat_html_content += f"""
                    <p class='chat-multi-item' style="margin-bottom: 10px;">
                        <strong>{i+1}. 질문:</strong> {q}<br>
                        👉 <strong>답변:</strong> {a}
                    </p>
                    """
            elif display_type == "llm_answer":
                bot_answer = entry["content"].replace("\n", "<br>")
                chat_html_content += f"<p>🧾 <strong>답변:</strong><br>{bot_answer}</p>"
                
            chat_html_content += '</div></div>'

    scroll_iframe_script = """
    <script>
    setTimeout(function () {
        var anchor = document.getElementById("chat-scroll-anchor");
        if (anchor) {
            anchor.scrollIntoView({ behavior: "auto", block: "end" });
        }
    }, 0);
    </script>
    """
    return f"""
    <div id="chat-content-scroll-area">
        {chat_html_content}
        <div id="chat-scroll-anchor"></div>
    </div>
    {scroll_iframe_script}
    """

components.html(
    display_chat_html_content(),
    height=520,
    scrolling=True
)

# --- 입력창(폼) (이전과 동일) ---
with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        st.rerun()