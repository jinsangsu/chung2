import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import json
import difflib

# 기본 설정
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

# CSS 스타일 주입 (Streamlit 메인 앱에 적용될 스타일)
st.markdown("""
<style>
    /* Streamlit 기본 여백 제거 및 전체 페이지 레이아웃 조정 */
    html, body, #root, .stApp, .streamlit-container {
        height: 100%;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column; /* 세로 방향으로 요소 정렬 */
    }

    .stApp > header, .stApp > footer { /* Streamlit 기본 헤더/푸터 숨기기 */
        visibility: hidden;
        height: 0px !important;
    }
    .stApp > .main { /* 메인 콘텐츠 영역 여백 제거 */
        padding: 0 !important;
        flex-grow: 1; /* 남은 공간을 차지하도록 설정 */
        display: flex;
        flex-direction: column;
    }
    /* Streamlit의 .block-container는 중앙 정렬의 주 요소이므로,
       여기에 flex-grow를 주어 남은 수직 공간을 차지하게 하고
       내부 콘텐츠를 수직으로 배열 */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        max-width: 700px; /* block-container의 최대 너비를 명시적으로 제한 */
        margin-left: auto; /* 중앙 정렬 */
        margin-right: auto; /* 중앙 정렬 */
    }

    /* 캐릭터 및 소개 영역 */
    .character-intro {
        flex-shrink: 0; /* 이 영역은 크기가 줄어들지 않음 */
        margin-bottom: 15px; /* 캐릭터 아래 간격 */
    }

    /* 입력 폼 컨테이너 (하단에 고정) */
    .stForm {
        flex-shrink: 0; /* 입력 폼은 줄어들지 않도록 */
        background-color: white;
        padding: 10px 20px;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
        z-index: 1000;
        width: 100%;
        max-width: 700px; /* block-container와 동일하게 최대 너비 제한 */
        margin-left: auto; /* 중앙 정렬 */
        margin-right: auto; /* 중앙 정렬 */
        position: sticky; /* 하단 고정 (Streamlit 환경에서 더 잘 작동) */
        bottom: 0;
    }
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding-right: 40px;
    }
    .stButton > button {
        border-radius: 20px;
    }

    /* 채팅 메시지 스타일 */
    .message-row {
        display: flex;
        margin-bottom: 10px;
        width: 100%;
    }
    .user-message-row {
        justify-content: flex-end;
    }
    .bot-message-row {
        justify-content: flex-start;
    }
    .message-bubble {
        max-width: 70%;
        padding: 8px 12px;
        border-radius: 15px;
        word-wrap: break-word;
    }
    .user-bubble {
        background-color: #dcf8c6;
        color: #333;
    }
    .bot-bubble {
        background-color: #e0f7fa;
        color: #333;
    }
    .chat-multi-item {
        margin-left: 25px;
        font-size: 0.9em;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)


# 캐릭터 영역
col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("managerbot_character.webp", width=100)
    except:
        st.warning("❗ 캐릭터 이미지를 불러올 수 없습니다.")
with col2:
    st.markdown("""
        <div class="character-intro">
            <h2 style='margin-top:25px;'>사장님, 안녕하세요!</h2>
            <p>저는 앞으로 사장님들 업무를 도와드리는<br>
            <strong>충청호남본부 매니저봇 ‘애순’</strong>이에요.</p>
            <p>매니저님께 여쭤보시기 전에<br>
            저 애순이한테 먼저 물어봐 주세요!<br>
            제가 아는 건 바로, 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
            늘 옆에서 든든하게 함께하겠습니다.</p>
            <strong>잘 부탁드려요! 😊</strong>
        </div>
    """, unsafe_allow_html=True)

# 구글 시트 연결
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# 세션 상태에 채팅 기록 저장
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []
# 세션 상태에 스크롤 플래그 초기화 - 이 플래그는 이제 메인 페이지 스크롤 대신 iframe 스크롤에만 집중
if "scroll_to_bottom_flag" not in st.session_state:
    st.session_state.scroll_to_bottom_flag = False

# ✅ 질문 처리 함수
def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

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

        # 사용자 질문 먼저 추가
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        # 봇 답변 생성 및 추가
        if len(matched) == 1:
            bot_answer_content = matched[0]["답변"]
            bot_display_type = "single_answer"
        elif len(matched) > 1:
            bot_answer_content = [{"q": r["질문"], "a": r["답변"]} for r in matched]
            bot_display_type = "multi_answer"
        else:
            bot_answer_content = "❌ 해당 질문에 대한 답변을 찾을 수 없습니다."
            bot_display_type = "single_answer"

        st.session_state.chat_log.append({
            "role": "bot",
            "content": bot_answer_content,
            "display_type": bot_display_type
        })
        # 새로운 메시지가 추가되면 스크롤 플래그 설정
        st.session_state.scroll_to_bottom_flag = True

    except Exception as e:
        # 오류 발생 시 오류 메시지 봇 답변 추가
        st.session_state.chat_log.append({
            "role": "bot",
            "content": f"❌ 오류 발생: {e}",
            "display_type": "single_answer"
        })
        st.session_state.scroll_to_bottom_flag = True

# 채팅 내용을 HTML로 출력하는 함수
def display_chat_html_content():
    chat_html_content = ""
    for entry in st.session_state.chat_log:
        if entry["role"] == "user":
            chat_html_content += f"""
            <div class="message-row user-message-row">
                <div class="message-bubble user-bubble">
                    <p><strong>❓ 질문:</strong> {entry['content']}</p>
                </div>
            </div>
            """
        elif entry["role"] == "bot":
            chat_html_content += f"""
            <div class="message-row bot-message-row">
                <div class="message-bubble bot-bubble">
            """
            if entry["display_type"] == "single_answer":
                chat_html_content += f"<p>🧾 <strong>답변:</strong> {entry['content']}</p>"
            elif entry["display_type"] == "multi_answer":
                chat_html_content += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
                for i, pair in enumerate(entry["content"]):
                    chat_html_content += f"<p class='chat-multi-item'><strong>{i+1}. 질문:</strong> {pair['q']}<br>👉 답변: {pair['a']}</p>"
          

    
    
    scroll_iframe_script = ""
    if st.session_state.scroll_to_bottom_flag:
        scroll_iframe_script = """
        <script>
        setTimeout(function () {
            const anchor = document.getElementById("chat-scroll-anchor");
            if (anchor) {
                anchor.scrollIntoView({ behavior: "smooth" });
            }
        }, 100);
        </script>
        """
        st.session_state.scroll_to_bottom_flag = False # <--- 이 부분 추가 (주의: iframe 안에서 플래그 초기화)


    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{
            margin: 0;
            font-family: sans-serif;
            display: flex;
            flex-direction: column;
            min-height: 100%; /* iframe 높이에 맞춤 */
            overflow-y: hidden; /* iframe 자체 스크롤바 숨김 */
        }}

        /* 채팅 내용 스크롤 영역 (iframe 내부에서 스크롤될 실제 영역) */
        #chat-content-scroll-area {{
            flex-grow: 1; /* 남은 공간을 모두 차지 */
            overflow-y: auto; /* 이 부분만 스크롤되도록 */
            padding: 10px;
            scroll-behavior: smooth; /* 부드러운 스크롤 */
            display: flex; /* Flexbox 사용하여 메시지 정렬 */
            flex-direction: column; /* 세로로 메시지 쌓기 */
            justify-content: flex-start; /* 메시지는 위에서 아래로 쌓이게 */
        }}

        /* 각 메시지 줄 컨테이너 (좌우 정렬) */
        .message-row {{
            display: flex;
            margin-bottom: 10px;
            width: 100%; /* 전체 너비 차지 */
        }}
        /* 사용자 메시지 (오른쪽 정렬) */
        .user-message-row {{
            justify-content: flex-end;
        }}
        /* 봇 메시지 (왼쪽 정렬) */
        .bot-message-row {{
            justify-content: flex-start;
        }}

        /* 메시지 버블 (내용) 스타일 */
        .message-bubble {{
            max-width: 70%; /* 메시지 버블 최대 너비 (조절 가능) */
            padding: 8px 12px;
            border-radius: 15px;
            word-wrap: break-word; /* 긴 텍스트 줄바꿈 */
        }}
        .user-bubble {{
            background-color: #dcf8c6; /* 사용자 메시지 배경색 */
            color: #333;
        }}
        .bot-bubble {{
            background-color: #e0f7fa; /* 봇 메시지 배경색 */
            color: #333;
        }}
        /* 유사 질문 들여쓰기 */
        .chat-multi-item {{
            margin-left: 25px; /* 유사 질문 들여쓰기 조정 */
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
    </style>
    </head>
    <body>
        <div id="chat-content-scroll-area" style="height: 400px; overflow-y: auto;">
              {chat_html_content}
              <div id="chat-scroll-anchor"></div>
        </div>
        {scroll_iframe_script}
    </body>
    </html>
    """

# 채팅 기록을 직접 렌더링
components.html(
    display_chat_html_content(),
    height=600, # 채팅창의 고정 높이 설정 (조절 가능)
    scrolling=False # iframe 자체에 스크롤바 허용
)


# 입력 폼
with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        st.rerun() # 중요: 채팅 기록 업데이트 후 앱을 다시 실행하여 UI 업데이트

# --- 자동 스크롤 JavaScript 주입 (메인 Streamlit 페이지 스크롤) ---
# 기존의 이 부분을 제거하거나 주석 처리합니다.
# if st.session_state.scroll_to_bottom_flag:
#     scroll_main_page_script = """
#     <script>
#         function scrollToMainContentBottom() {
#             const mainContent = document.querySelector('.stApp .main');
#             if (mainContent) {
#                 mainContent.scrollTop = mainContent.scrollHeight;
#             } else {
#                 window.scrollTo(0, document.body.scrollHeight);
#             }
#         }
#         setTimeout(scrollToMainContentBottom, 150);
#     </script>
#     """
#     components.html(scroll_main_page_script, height=0, width=0)
#     st.session_state.scroll_to_bottom_flag = False