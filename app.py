import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import json
import difflib

# 기본 설정
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="wide") # layout="wide"로 변경하여 더 넓은 공간 확보

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
    .block-container { /* 컨테이너 내부 여백 조정 */
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        flex-grow: 1; /* 남은 공간을 차지하도록 설정 */
        display: flex;
        flex-direction: column;
    }

    /* 캐릭터 및 소개 영역 */
    .character-intro {
        flex-shrink: 0; /* 이 영역은 크기가 줄어들지 않음 */
        margin-bottom: 15px; /* 캐릭터 아래 간격 */
    }

    /* 입력 폼 컨테이너 (하단에 고정 시도) */
    .stForm {
        flex-shrink: 0; /* 입력 폼은 줄어들지 않도록 */
        background-color: white;
        padding: 10px 20px;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
        z-index: 1000;
        width: 100%;
        max-width: 700px; /* Streamlit main 컨테이너의 기본 최대 너비와 맞춤 */
        margin-left: auto; /* 중앙 정렬 */
        margin-right: auto; /* 중앙 정렬 */
        /* `position: sticky; bottom: 0;`는 Streamlit 환경에서 불안정할 수 있으므로, 
           이 CSS는 Streamlit의 .stForm이 고정되도록 시도합니다. */
        position: sticky; 
        bottom: 0; 
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
if "scroll_to_bottom" not in st.session_state:
    st.session_state.scroll_to_bottom = False

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

        if len(matched) == 1:
            st.session_state.chat_log.append({
                "type": "single",
                "role": "user", # 역할 추가
                "question": question_input,
                "answer": matched[0]["답변"]
            })
            # 봇 답변 추가 (사용자 질문에 대한 봇의 답변)
            st.session_state.chat_log.append({
                "type": "single",
                "role": "bot", # 역할 추가
                "question": "", # 봇은 질문하지 않으므로 비워둠
                "answer": matched[0]["답변"]
            })
        elif len(matched) > 1:
            st.session_state.chat_log.append({
                "type": "multi",
                "role": "user", # 역할 추가
                "question": question_input,
                "matches": [{"q": r["질문"], "a": r["답변"]} for r in matched]
            })
            # 봇 답변 추가 (유사 질문 목록)
            st.session_state.chat_log.append({
                "type": "multi",
                "role": "bot", # 역할 추가
                "question": "",
                "matches": [{"q": r["질문"], "a": r["답변"]} for r in matched]
            })
        else:
            st.session_state.chat_log.append({
                "type": "single",
                "role": "user", # 역할 추가
                "question": question_input,
                "answer": "❌ 해당 질문에 대한 답변을 찾을 수 없습니다."
            })
            # 봇 답변 추가 (답변을 찾을 수 없을 때)
            st.session_state.chat_log.append({
                "type": "single",
                "role": "bot", # 역할 추가
                "question": "",
                "answer": "❌ 해당 질문에 대한 답변을 찾을 수 없습니다."
            })
    except Exception as e:
        st.session_state.chat_log.append({
            "type": "single",
            "role": "user", # 역할 추가
            "question": question_input,
            "answer": f"❌ 오류 발생: {e}"
        })
        st.session_state.chat_log.append({
            "type": "single",
            "role": "bot", # 역할 추가
            "question": "",
            "answer": f"❌ 오류 발생: {e}"
        })

# 채팅 기록을 표시할 placeholder (st.empty() 사용)
chat_history_placeholder = st.empty()

# 채팅 내용을 HTML로 출력하는 함수
def display_chat_html_content(): # 함수 이름 변경
    chat_html_content = ""
    for qa in st.session_state.chat_log:
        # 메시지 컨테이너에 role에 따른 클래스 추가
        if qa["role"] == "user": # 사용자 메시지
            message_class = "user-message-row"
            question_icon = "❓"
            # 사용자 메시지에는 답변 아이콘 필요 없음
        elif qa["role"] == "bot": # 봇 메시지
            message_class = "bot-message-row"
            question_icon = "" # 봇은 질문하지 않으므로 아이콘 비워둠
            answer_icon = "🧾" # 봇 답변 아이콘

        if qa["role"] == "user": # 사용자 질문만 표시
            chat_html_content += f"""
            <div class="message-row {message_class}">
                <div class="message-bubble user-bubble">
                    <p><strong>{question_icon} 질문:</strong> {qa['question']}</p>
                </div>
            </div>
            """
        elif qa["role"] == "bot": # 봇 답변만 표시
            chat_html_content += f"""
            <div class="message-row {message_class}">
                <div class="message-bubble bot-bubble">
            """
            if qa["type"] == "single":
                chat_html_content += f"<p>{answer_icon} <strong>답변:</strong> {qa['answer']}</p>"
            elif qa["type"] == "multi":
                chat_html_content += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
                for i, pair in enumerate(qa["matches"]):
                    chat_html_content += f"<p class='chat-multi-item'><strong>{i+1}. 질문:</strong> {pair['q']}<br>{answer_icon} 답변: {pair['a']}</p>"
            chat_html_content += "</div></div>"
    
    # 스크롤 타겟 마커
    chat_html_content += "<div id='scroll_to_here' style='height:1px;'></div>"
    
    # 이제 이 HTML을 iframe 내부에서 렌더링할 때 사용할 CSS를 포함
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
            justify-content: flex-end; /* 내용을 아래에서부터 채움 */
            min-height: 100%; /* iframe 높이에 맞춤 */
            overflow-y: hidden; /* iframe 자체 스크롤 숨기고, 내부 div가 스크롤되도록 */
        }}
        
        /* 전체 메시지 컨테이너 (이것이 스크롤될 것임) */
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
            max-width: 70%; /* 메시지 버블 최대 너비 */
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
    <body>
        <div id="chat-content-scroll-area">
            {chat_html_content}
        </div>
    </body>
    </html>
    """

# 채팅 기록을 chat_history_placeholder에 표시
# st.components.v1.html을 사용하여 HTML을 iframe 내에 렌더링
with chat_history_placeholder.container():
    components.html(
        display_chat_html_content(),
        height=400, # 채팅창의 고정 높이 설정 (조절 가능)
        scrolling=True # iframe 자체에 스크롤바 허용
    )


# 입력 폼
with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        st.session_state.scroll_to_bottom = True # 스크롤을 위한 플래그 설정
        st.rerun()

# 새로운 답변이 추가될 때마다 자동으로 스크롤 (iframe 내부 스크롤)
if st.session_state.get("scroll_to_bottom"):
    components.html("""
    <script>
        // iframe 내부의 document에 접근하여 스크롤 제어
        // iframe의 title을 사용하여 정확한 iframe을 찾음
        const iframe = window.parent.document.querySelector('iframe[title*="Streamlit Component"]');
        if (iframe && iframe.contentWindow && iframe.contentWindow.document) {
            const chatScrollArea = iframe.contentWindow.document.getElementById("chat-content-scroll-area");
            if (chatScrollArea) {
                chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
            }
        }
    </script>
    """, height=0, scrolling=False)
    st.session_state.scroll_to_bottom = False # 스크롤 플래그 초기화