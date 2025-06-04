import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components # Make sure this is imported
import json
import difflib

# 기본 설정
# layout="centered"로 변경하여 앱의 콘텐츠가 중앙에 위치하고 기본 너비가 제한되도록 함
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
        position: sticky; /* 하단 고정 시도 (Streamlit 환경에서 불안정할 수 있음) */
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
# st.session_state.scroll_to_bottom 플래그는 더 이상 필요 없으므로 삭제

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
            "display_type": "question" # 사용자 질문은 항상 'question' 타입으로 표시
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
            "display_type": bot_display_type # 봇 답변 타입
        })

    except Exception as e:
        # 오류 발생 시 오류 메시지 봇 답변 추가
        st.session_state.chat_log.append({
            "role": "bot",
            "content": f"❌ 오류 발생: {e}",
            "display_type": "single_answer"
        })

# 채팅 내용을 HTML로 출력하는 함수
def display_chat_html_content():
    chat_html = ""
    for entry in st.session_state.chat_log:
        if entry["role"] == "user":
            chat_html += f"""
            <div style="text-align:right; color:#333; margin-bottom:5px;">
                <b>❓ 질문:</b> {entry['content']}
            </div>
            """
        elif entry["role"] == "bot":
            if entry["display_type"] == "single_answer":
                chat_html += f"""
                <div style="text-align:left; background:#eef; padding:8px; border-radius:10px; margin-bottom:10px;">
                    <b>🧾 답변:</b> {entry['content']}
                </div>
                """
            elif entry["display_type"] == "multi_answer":
                chat_html += """
                <div style="text-align:left; background:#eef; padding:8px; border-radius:10px; margin-bottom:10px;">
                    <b>🔎 유사한 질문이 여러 개 있습니다:</b><br>
                """
                for i, pair in enumerate(entry["content"]):
                    chat_html += f"""
                    <div style="margin-left:15px;">{i+1}. <b>{pair['q']}</b><br>👉 {pair['a']}</div><br>
                    """
                chat_html += "</div>"

    # 마지막 앵커
    chat_html += "<div id='bottom-anchor'></div>"

    # 스크롤 스크립트
    chat_html += """
    <script>
        const anchor = document.getElementById("bottom-anchor");
        if (anchor) {
            anchor.scrollIntoView({ behavior: "smooth", block: "end" });
        }
    </script>
    """
    return chat_html

    # JavaScript to scroll to the bottom, this will be executed when the iframe content loads/updates
    # setTimeout을 DOMContentLoaded로 변경하여 더 안정적으로 스크롤
    scroll_script = """
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const chatScrollArea = document.getElementById("chat-content-scroll-area");
            if (chatScrollArea) {
                chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
            }
        });
    </script>
    """
st.markdown(display_chat_html_content(), unsafe_allow_html=True)

# 채팅 기록을 표시할 placeholder (st.empty() 사용) 이 부분은 이제 필요 없습니다.
# chat_history_placeholder = st.empty()



# 입력 폼
with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        # st.session_state.scroll_to_bottom = True # 이 줄은 더 이상 필요 없음
        st.rerun() # 중요: 채팅 기록 업데이트 후 앱을 다시 실행하여 UI 업데이트


