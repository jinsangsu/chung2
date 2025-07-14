import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import requests
import base64
import os
from collections import Counter
import re

API_URL = "https://chung2.fly.dev/chat"

st.set_page_config(page_title="애순이 설계사 Q&A", page_icon="💬", layout="centered")

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
#chat-content-scroll-area {
    flex-grow: 1;
    overflow-y: auto !important;
    padding: 10px 0 0 0;
    scroll-behavior: smooth;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    background: #fff;
    height: 420px;
    min-height: 320px;
    max-width: 700px;
}
.message-row {
    display: flex;
    margin-bottom: 12px;
    width: 100vw !important;
    max-width: 700px !important;
}
.bot-message-row, .intro-message-row { justify-content: flex-start !important; }
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
.chat-multi-item {
    margin-left: 25px;
    font-size: 0.98em;
    margin-bottom: 5px;
}
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
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "intro", "content": "", "display_type": "intro"}]
if "scroll_to_bottom_flag" not in st.session_state:
    st.session_state.scroll_to_bottom_flag = False
if "pending_keyword" not in st.session_state:
    st.session_state.pending_keyword = None

def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

def normalize_text(text):
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", text.lower())

def add_friendly_prefix(answer):
    answer = answer.strip()
    if answer[:7].replace(" ", "").startswith("사장님"):
        return answer
    else:
        return f"사장님, {answer} 이렇게 처리하시면 됩니다!"

def extract_main_keywords(questions, exclude_terms=None, topn=5):
    # konlpy 없이 명사 근사 추출(2~5글자 한글+패턴 필터)
    if exclude_terms is None:
        exclude_terms = []
    exclude_terms_norm = [normalize_text(term) for term in exclude_terms]
    candidate_words = []
    stopwords = set([
        "질문", "답변", "경우", "보험", "사장님", "수", "및", "의", "을", "를", "에", "에서", "로", "으로",
        "이", "가", "도", "는", "한", "해당", "등", "및", "의", "와", "과", "요", "때", "더", "도", "만",
        "는지", "이상", "사항", "관련", "필요", "있나요", "및", "그런데", "하기", "방법", "내용", "여부", "했는데"
    ])
    for q in questions:
        for w in re.findall(r"[가-힣]{2,5}", q):  # 한글 2~5글자
            w_norm = normalize_text(w)
            if w_norm in exclude_terms_norm or w_norm in stopwords:
                continue
            # 조사/어미/동사 패턴 끝 필터
            if re.search(r"(하다|되다|있다|없다|된다|한|는|가|로|을|를|요|고|의|에|과|와|든지|등|까지|까지요|에게|만|이라|거나|에서|로부터|에게서|부터|하는|받는|할까|한가요|하고|되고|인가요)$", w):
                continue
            candidate_words.append(w)
    normalized = [normalize_text(w) for w in candidate_words]
    mapping = {}
    for w, n in zip(candidate_words, normalized):
        if n not in mapping:
            mapping[n] = w
    count = Counter(normalized)
    return [mapping[n] for n, c in count.most_common(topn) if c > 0][:topn]

def handle_question(question_input):
    SIMILARITY_THRESHOLD = 0.4
    if st.session_state.pending_keyword:
        user_input = st.session_state.pending_keyword + " " + question_input
        st.session_state.pending_keyword = None
    else:
        user_input = question_input

    try:
        records = sheet.get_all_records()
        q_input_norm = normalize_text(user_input)
        matched = []
        for r in records:
            sheet_q_norm = normalize_text(r["질문"])
            if (
                (q_input_norm in sheet_q_norm) or
                (sheet_q_norm in q_input_norm) or
                (get_similarity_score(q_input_norm, sheet_q_norm) >= SIMILARITY_THRESHOLD)
            ):
                matched.append(r)
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        if len(matched) >= 5:
            user_terms = [w for w in re.findall(r"[가-힣a-zA-Z0-9]{2,8}", question_input) if len(w) > 1]
            keywords = extract_main_keywords([r['질문'] for r in matched], exclude_terms=user_terms)
            keyword_str = ", ".join(keywords)
            st.session_state.pending_keyword = user_input
            st.session_state.chat_log.append({
                "role": "bot",
                "content": f"사장님, {keywords[0]}의 어떤 부분이 궁금하신가요? 예) {keyword_str} 등<br>궁금한 점을 더 구체적으로 입력해 주세요!",
                "display_type": "pending"
            })
            st.session_state.scroll_to_bottom_flag = True
            return

        if len(matched) == 1:
            bot_answer_content = {
                "q": matched[0]["질문"],
                "a": add_friendly_prefix(matched[0]["답변"])
            }
            bot_display_type = "single_answer"
        elif len(matched) > 1:
            bot_answer_content = []
            for r in matched:
                bot_answer_content.append({
                    "q": r["질문"],
                    "a": add_friendly_prefix(r["답변"])
                })
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
        if len(matched) > 0:
            st.session_state.chat_log.append({
                "role": "bot",
                "content": bot_answer_content,
                "display_type": bot_display_type
            })
        st.session_state.scroll_to_bottom_flag = True
    except Exception as e:
        st.session_state.chat_log.append({
            "role": "bot",
            "content": f"❌ 오류 발생: {e}",
            "display_type": "llm_answer"
        })
        st.session_state.scroll_to_bottom_flag = True

def display_chat_html_content():
    chat_html_content = ""
    for entry in st.session_state.chat_log:
        if entry["role"] == "intro":
            chat_html_content += f'<div class="message-row intro-message-row"><div class="message-bubble intro-bubble">{get_intro_html()}</div></div>'
        elif entry["role"] == "user":
            user_question = entry["content"].replace("\n", "<br>")
            chat_html_content += (
                '<div class="message-row user-message-row" style="display:flex;justify-content:flex-end;width:100%;">'
                '<div class="message-bubble user-bubble" '
                'style="background:#dcf8c6;color:#111;font-weight:700;'
                'text-align:center; margin-left:auto; min-width:80px; display:inline-block;'
                'padding:12px 32px 12px 32px; border-radius:15px;">'
                f'{user_question}'
                '</div></div>'
            )
        elif entry["role"] == "bot":
            if entry.get("display_type") == "single_answer":
                q = entry['content']['q'].replace('\n', '<br>')
                a = entry['content']['a'].replace('\n', '<br>')
                chat_html_content += (
                    '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                    f"<p style='margin-bottom: 8px;'><strong>질문:</strong> {q}</p>"
                    f"<p>👉 <strong>답변:</strong> {a}</p>"
                    '</div></div>'
                )
            elif entry.get("display_type") == "multi_answer":
                chat_html_content += "<div class='message-row bot-message-row'><div class='message-bubble bot-bubble'>"
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
                chat_html_content += "</div></div>"
            elif entry.get("display_type") == "pending":
                chat_html_content += (
                    '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                    f"<p style='color:#ff914d;font-weight:600;'>{entry['content']}</p>"
                    '</div></div>'
                )
            elif entry.get("display_type") == "llm_answer":
                bot_answer = entry["content"].replace("\n", "<br>")
                chat_html_content += (
                    '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                    f"<p>🧾 <strong>답변:</strong><br>{bot_answer}</p>"
                    '</div></div>'
                )
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

with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("질문하기")
    if submitted and question_input:
        handle_question(question_input)
        st.rerun()
