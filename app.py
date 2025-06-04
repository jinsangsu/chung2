
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import json
import difflib

# 기본 설정
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="wide") # layout="wide"로 변경하여 더 넓은 공간 확보

# CSS 스타일 주입 (수정된 부분)
# Streamlit의 기본 레이아웃 위에 CSS를 덮어씌우는 방식
st.markdown("""
<style>
    /* Streamlit 기본 여백 제거 */
    .stApp {
        padding: 0px !important;
    }
    .main {
        padding: 0px !important;
    }
    .block-container {
        padding-top: 1rem; /* 상단 여백 최소화 */
        padding-bottom: 0rem; /* 하단 여백 제거 */
        padding-left: 1rem;
        padding-right: 1rem;
    }
    header, footer {
        visibility: hidden; /* Streamlit 기본 헤더/푸터 숨기기 */
        height: 0px !important;
    }

    /* 전체 레이아웃 (캐릭터, 채팅창, 입력창을 포함하는 가장 큰 컨테이너) */
    html, body, #root, .stApp, .streamlit-container {
        height: 100%;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column; /* 세로 방향으로 정렬 */
    }

    /* 채팅 컨테이너 스타일 */
    #chat-history-container {
        flex-grow: 1; /* 남은 공간을 모두 차지하도록 설정 */
        overflow-y: auto; /* 이 부분만 스크롤되도록 */
        padding: 10px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 10px; /* 입력창과의 간격 */
        background-color: #f9f9f9;
        display: flex; /* flexbox를 사용하여 내용을 아래로 밀어넣음 */
        flex-direction: column;
        justify-content: flex-end; /* 내용이 아래에서부터 채워지도록 */
    }

    /* 입력 폼 컨테이너 (하단에 고정) */
    .stForm {
        flex-shrink: 0; /* 입력 폼은 줄어들지 않도록 */
        background-color: white;
        padding: 10px 20px;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -2px 5px rgba(0,0,0,0.05);
        z-index: 1000;
        width: 100%; /* 부모 너비에 맞춤 */
        margin-left: auto; /* 중앙 정렬 */
        margin-right: auto; /* 중앙 정렬 */
        max-width: 700px; /* Streamlit main 컨테이너의 기본 최대 너비에 맞춤 */
        position: -webkit-sticky; /* For Safari */
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


# 캐릭터 영역 (기존과 동일)
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

# 구글 시트 연결 (기존과 동일)
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
                "question": question_input,
                "answer": matched[0]["답변"]
            })
        elif len(matched) > 1:
            st.session_state.chat_log.append({
                "type": "multi",
                "question": question_input,
                "matches": [{"q": r["질문"], "a": r["답변"]} for r in matched]
            })
        else:
            st.session_state.chat_log.append({
                "type": "single",
                "question": question_input,
                "answer": "❌ 해당 질문에 대한 답변을 찾을 수 없습니다."
            })
    except Exception as e:
        st.session_state.chat_log.append({
            "type": "single",
            "question": question_input,
            "answer": f"❌ 오류 발생: {e}"
        })

# 채팅 기록을 표시할 placeholder
# st.empty()를 사용하되, CSS ID를 부여하여 JavaScript에서 쉽게 접근하도록 함
chat_history_placeholder = st.empty()

# 채팅 내용을 HTML로 출력하는 함수
def display_chat_log():
    chat_html = ""
    for qa in st.session_state.chat_log:
        chat_html += f"""
        <div style="margin-bottom: 10px;">
            <p style="margin-bottom: 2px;"><strong>❓ 질문:</strong> {qa['question']}</p>
        """
        if qa["type"] == "single":
            chat_html += f"<p style='background-color:#e0f7fa; padding:8px; border-radius:5px;'>🧾 <strong>답변:</strong> {qa['answer']}</p>"
        elif qa["type"] == "multi":
            chat_html += "<p style='margin-bottom: 5px;'>🔎 유사한 질문이 여러 개 있습니다:</p>"
            for i, pair in enumerate(qa["matches"]):
                chat_html += f"<p style='margin-left: 15px;'><strong>{i+1}. 질문:</strong> {pair['q']}<br>👉 답변: {pair['a']}</p>"
        chat_html += "</div>" # 각 대화 단위 div 닫기
    
    # 스크롤 타겟 마커
    chat_html += "<div id='scroll_to_here' style='height:1px;'></div>" 
    
    return chat_html

# 채팅 기록을 chat_history_placeholder에 표시
with chat_history_placeholder.container():
    # 이제 이 div가 CSS의 #chat-history-container 스타일을 받음
    st.markdown(f"""
    <div id="chat-history-container">
        {display_chat_log()}
    </div>
    """, unsafe_allow_html=True)


# 입력 폼
# 이 폼은 CSS의 .stForm 스타일에 의해 하단에 고정되도록 시도
with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        st.session_state.scroll_to_bottom = True # 스크롤을 위한 플래그 설정
        st.rerun()

# 새로운 답변이 추가될 때마다 자동으로 스크롤
if st.session_state.get("scroll_to_bottom"):
    components.html("""
    <script>
        const chatContainer = document.getElementById("chat-history-container");
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    </script>
    """, height=0, scrolling=False)
    st.session_state.scroll_to_bottom = False # 스크롤 플래그 초기화