import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import json
from io import StringIO
import difflib

# 기본 설정
st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

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

# CSS 스타일 주입 (채팅창 고정 및 입력창 고정을 위한 시도)
# Streamlit의 기본 레이아웃 위에 CSS를 덮어씌우는 방식
st.markdown("""
<style>
    /* 전체 페이지 레이아웃 조정 (Streamlit 기본 마진 제거 등) */
    .main {
        padding-top: 0rem;
        padding-bottom: 0rem;
    }
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    header {
        visibility: hidden; /* Streamlit 헤더 숨기기 */
        height: 0px;
    }
    footer {
        visibility: hidden; /* Streamlit 푸터 숨기기 */
        height: 0px;
    }

    /* 채팅 컨테이너 고정 (Chat UI의 본질적인 부분) */
    #chat-container {
        height: calc(100vh - 200px); /* 화면 높이에서 입력창 높이 등을 제외 */
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 10px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column; /* 내용을 위에서 아래로 쌓이게 */
        justify-content: flex-end; /* 내용을 아래에 붙이고, 스크롤하면 위로 올라가게 */
    }

    /* 입력창 컨테이너 고정 (하단에 항상 보이게) */
    .stForm { /* Streamlit 폼에 적용되는 기본 클래스 */
        position: fixed; /* 화면에 고정 */
        bottom: 0; /* 화면 하단에 붙임 */
        left: 50%; /* 중앙 정렬을 위한 초기 위치 */
        transform: translateX(-50%); /* 중앙 정렬 */
        width: 100%; /* 너비 100% */
        max-width: 700px; /* main 컨테이너의 최대 너비와 맞춤 */
        background-color: white; /* 배경색 지정 */
        padding: 10px 20px; /* 패딩 */
        border-top: 1px solid #eee; /* 상단 구분선 */
        box-shadow: 0 -2px 5px rgba(0,0,0,0.1); /* 그림자 효과 */
        z-index: 1000; /* 다른 요소 위에 오도록 */
    }
    /* Streamlit 텍스트 입력과 버튼도 CSS를 통해 조정 */
    .stTextInput > div > div > input {
        border-radius: 20px;
        padding-right: 40px; /* 버튼 공간 확보 */
    }
    .stButton > button {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)


# 채팅 내용을 HTML로 출력하는 함수
def display_chat_log():
    chat_html = ""
    for qa in st.session_state.chat_log:
        chat_html += f"""
        <div style="margin-bottom: 10px;">
            <p><strong>❓ 질문:</strong> {qa['question']}</p>
        """
        if qa["type"] == "single":
            chat_html += f"<p style='background-color:#e0f7fa; padding:8px; border-radius:5px;'>🧾 <strong>답변:</strong> {qa['answer']}</p>"
        elif qa["type"] == "multi":
            chat_html += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
            for i, pair in enumerate(qa["matches"]):
                chat_html += f"<p><strong>{i+1}. 질문:</strong> {pair['q']}<br>👉 답변: {pair['a']}</p>"
        chat_html += "</div>" # 각 대화 단위 div 닫기
    
    # 이 마커는 실제 스크롤 타겟이 아니라, 단순히 채팅 내용의 끝을 나타냄
    # 스크롤은 #chat-container의 scrollHeight를 이용
    chat_html += "<div id='end_of_chat_marker' style='height:1px;'></div>" 
    
    return chat_html

# ✅ 채팅 기록을 표시할 컨테이너 (이전에 chat_placeholder로 사용했던 부분)
# 이제 이 컨테이너에 직접적인 CSS ID를 부여하여 JavaScript에서 제어
# 채팅 내용이 쌓이는 div의 id를 'chat-container'로 지정
st.markdown(f"""
<div id="chat-container">
    {display_chat_log()}
</div>
""", unsafe_allow_html=True)


# ✅ 입력 폼 (이전에 input_area_container로 사용했던 부분)
# 이제 form 자체가 CSS로 고정되므로 별도의 st.container() 래핑 불필요
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
      setTimeout(() => {
        const chatContainer = document.getElementById("chat-container");
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight; // 채팅창의 가장 아래로 스크롤
        }
      }, 100); // 딜레이를 더 줄여 거의 즉시 스크롤되도록 시도
    </script>
    """, height=0, scrolling=False)
    st.session_state.scroll_to_bottom = False # 스크롤 플래그 초기화
