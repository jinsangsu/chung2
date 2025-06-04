
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

# ✅ 질문 처리
if "input_submitted" not in st.session_state:
    st.session_state.input_submitted = False
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

if st.session_state.input_submitted:
    handle_question(st.session_state.input_text)
    st.session_state.input_submitted = False


# 💬 채팅 내용 HTML로 출력
chat_html = ""

for qa in st.session_state.chat_log:
    chat_html += f"<p><strong>❓ 질문:</strong> {qa['question']}</p>"
    if qa["type"] == "single":
        chat_html += f"<p style='background-color:#e0f7fa; padding:8px; border-radius:5px;'>🧾 <strong>답변:</strong> {qa['answer']}</p>"
    elif qa["type"] == "multi":
        chat_html += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
        for i, pair in enumerate(qa["matches"]):
            chat_html += f"<p><strong>{i+1}. 질문:</strong> {pair['q']}<br>👉 답변: {pair['a']}</p>"

st.markdown(
    f"""
    <div id="chatbox" style="
        height: 50vh;
        overflow-y: auto;
        padding: 10px;
        border: 1px solid #ccc;
        border-radius: 10px;
        margin-bottom: 10px;
        scroll-behavior: smooth;
    ">
        {chat_html}
    </div>
        """,
    unsafe_allow_html=True
)
components.html("""
<script>
  const chatbox = document.getElementById("chatbox");
  if (chatbox) {
    const observer = new MutationObserver(() => {
      chatbox.scrollTop = chatbox.scrollHeight;
    });
    observer.observe(chatbox, { childList: true, subtree: true });
  }
</script>
""", height=0)

#🔻 채팅 입력창과 확실히 분리
st.markdown("""
<style>
#input-container {
    position: sticky;
    bottom: 0;
    background-color: white;
    padding-top: 10px;
    z-index: 100;
}
</style>
<div id="input-container">
""", unsafe_allow_html=True)
# ✅ 입력 폼
input_container = st.container()
with input_container:
    with st.form("input_form", clear_on_submit=True):
        question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
        submitted = st.form_submit_button("질문하기")
        if submitted and question_input:
            handle_question(question_input)
            st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

