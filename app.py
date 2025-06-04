import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import json
from io import StringIO
import difflib

# 기본 설정
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

# 캐릭터 영역
col1, col2 = st.columns([1, 4])
with col1:
    try:
        st.image("managerbot_character.webp", width=100)
    except:
        st.warning("❗ 캐릭터 이미지를 불러올 수 없습니다.")
with col2:
    st.markdown("""
        <h2 style='margin-top:25px;'>사장님, 안녕하세요!</h2>
        <p>저는 앞으로 사장님들 업무를 도와드리는<br>
        <strong>충청호남본부 매니저봇 ‘애순’</strong>이에요.</p>
        <p>매니저님께 여쭤보시기 전에<br>
        저 애순이한테 먼저 물어봐 주세요!<br>
        제가 아는 건 바로, 친절하게 알려드릴게요!</p>
        <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
        늘 옆에서 든든하게 함께하겠습니다.</p>
        <strong>잘 부탁드려요! 😊</strong>
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
if "scroll_to_bottom" not in st.session_state: # 스크롤 플래그 초기화
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
        elif len(matched) > 1:
            st.session_state.chat_log.append({
                "type": "multi",
                "role": "user", # 역할 추가
                "question": question_input,
                "matches": [{"q": r["질문"], "a": r["답변"]} for r in matched]
            })
        else:
            st.session_state.chat_log.append({
                "type": "single",
                "role": "user", # 역할 추가
                "question": question_input,
                "answer": "❌ 해당 질문에 대한 답변을 찾을 수 없습니다."
            })
    except Exception as e:
        st.session_state.chat_log.append({
            "type": "single",
            "role": "user", # 역할 추가
            "question": question_input,
            "answer": f"❌ 오류 발생: {e}"
        })

# 💬 채팅 내용을 표시할 placeholder
chat_placeholder = st.empty()

# 채팅 내용을 HTML로 출력하는 함수
def display_chat_log():
    chat_html = ""
    for qa in st.session_state.chat_log:
        # 메시지 컨테이너에 role에 따른 클래스 추가
        if qa["role"] == "user": # 사용자 메시지
            message_class = "user-message-container"
            question_icon = "❓"
            answer_icon = "👉" # 사용자 답변에 대한 아이콘 변경
        else: # 봇 메시지 (여기서는 애순이봇)
            message_class = "bot-message-container"
            question_icon = "💬" # 봇의 질문 아이콘 (애순이봇이 질문하지는 않으므로 사용 안될 수 있음)
            answer_icon = "🧾" # 봇 답변 아이콘

        chat_html += f"""
        <div class="message-row {message_class}">
            <div class="message-bubble">
                <p><strong>{question_icon} 질문:</strong> {qa['question']}</p>
        """
        if qa["type"] == "single":
            chat_html += f"<p class='bot-answer-bubble'> {answer_icon} <strong>답변:</strong> {qa['answer']}</p>"
        elif qa["type"] == "multi":
            chat_html += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
            for i, pair in enumerate(qa["matches"]):
                chat_html += f"<p style='margin-left: 15px;'><strong>{i+1}. 질문:</strong> {pair['q']}<br>{answer_icon} 답변: {pair['a']}</p>"
        chat_html += "</div></div>" # message-bubble, message-row 닫기
    
    # 더 이상 'latest_answer_marker' 마커를 사용하지 않음.
    # chat_html += "<div id='latest_answer_marker'></div>"
    
    return f"""
    <style>
        /* 채팅창 스타일 */
        #chatbox {{
            height: 50vh; /* 고정 높이 */
            overflow-y: auto; /* 스크롤 가능 */
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 10px;
            margin-bottom: 10px;
            scroll-behavior: smooth;
            display: flex; /* Flexbox 사용하여 메시지 정렬 */
            flex-direction: column; /* 세로로 메시지 쌓기 */
        }}

        /* 각 메시지 줄 컨테이너 */
        .message-row {{
            display: flex;
            margin-bottom: 10px;
        }}
        /* 사용자 메시지 (오른쪽 정렬) */
        .user-message-container {{
            justify-content: flex-end;
        }}
        /* 봇 메시지 (왼쪽 정렬) */
        .bot-message-container {{
            justify-content: flex-start;
        }}

        /* 메시지 버블 (내용) 스타일 */
        .message-bubble {{
            max-width: 70%; /* 메시지 버블 최대 너비 */
            padding: 8px 12px;
            border-radius: 15px;
            word-wrap: break-word; /* 긴 텍스트 줄바꿈 */
        }}
        .user-message-container .message-bubble {{
            background-color: #dcf8c6; /* 사용자 메시지 배경색 */
            color: #333;
        }}
        .bot-message-container .message-bubble {{
            background-color: #e0f7fa; /* 봇 메시지 배경색 */
            color: #333;
        }}
        .bot-answer-bubble {{ /* 봇 답변 (단일) 버블 */
            background-color: #e0f7fa;
            padding: 8px;
            border-radius: 5px;
        }}
        /* 유사 질문 들여쓰기 */
        .chat-multi-item {{
            margin-left: 15px;
            font-size: 0.9em;
        }}
    </style>
    <div id="chatbox">
        {chat_html}
    </div>
    """

# 채팅 기록을 chat_placeholder에 표시
with chat_placeholder.container():
    st.markdown(display_chat_log(), unsafe_allow_html=True)

# 🔻 채팅 입력창 (하단에 고정)
# 이전에 사용하던 #input-container 스타일은 Streamlit의 .stForm에 적용.
# CSS를 통해 하단에 고정하는 방식이므로, 별도의 st.container() 래핑은 필수가 아님.
# 그러나 레이아웃 관리를 위해 st.container()를 사용하는 것은 유효.
input_area_container = st.container()

with input_area_container:
    with st.form("input_form", clear_on_submit=True):
        question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
        submitted = st.form_submit_button("질문하기")
        if submitted and question_input:
            handle_question(question_input)
            st.session_state.scroll_to_bottom = True # 스크롤을 위한 플래그 설정
            st.rerun()

# 새로운 답변이 추가될 때마다 자동으로 스크롤
# ✅ 이 스크립트를 Streamlit 앱의 가장 마지막에 배치하여 렌더링 완료 후 실행되도록 유도
if st.session_state.get("scroll_to_bottom"):
    components.html("""
    <script>
      setTimeout(() => {
        const chatbox = document.getElementById("chatbox");
        if (chatbox) {
          chatbox.scrollTop = chatbox.scrollHeight; // 채팅창의 가장 아래로 스크롤
        }
      }, 50); // 딜레이를 줄여 더 빠르게 스크롤 (조절 가능)
    </script>
    """, height=0, scrolling=False) # scrolling=False 추가하여 불필요한 스크롤바 방지
    st.session_state.scroll_to_bottom = False # 스크롤 플래그 초기화