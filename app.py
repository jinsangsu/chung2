import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import requests
import base64
import os
import re
from collections import Counter

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
    if exclude_terms is None:
        exclude_terms = []
    exclude_terms_norm = [normalize_text(term) for term in exclude_terms]
    candidate_words = []
    stopwords = set([
        "질문", "답변", "경우", "사장님", "수", "및", "의", "을", "를", "에", "에서", "로", "으로",
        "이", "가", "도", "는", "한", "해당", "등", "와", "과", "요", "때", "더", "만",
        "는지", "이상", "사항", "관련", "필요", "있나요", "그런데", "하기", "방법", "내용", "여부", "했는데",
        "되었습니다", "됩니다", "되나요", "됐습니다", "합니다", "하였다", "됨", "함", "된다"
    ])
    for q in questions:
        for w in re.findall(r"[가-힣]{2,5}", q):  # 한글 2~5글자
            w_norm = normalize_text(w)
            if w_norm in exclude_terms_norm or w_norm in stopwords:
                continue
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
    user_txt = question_input.strip().replace(" ", "").lower()

    # [잡담/감정/상황별] 애순이 반응 확장
    if "애순" in user_txt:
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        # 상황/감정별 인식(키워드·멘트 자유롭게 추가)
        if "사랑" in user_txt:
            reply = "사장님, 저도 사랑합니다! 💛 언제나 사장님 곁에 있을게요!"
        elif "잘지냈" in user_txt or "안녕" in user_txt:
            reply = "네! 사장님 덕분에 잘 지내고 있습니다😊 사장님은 잘 지내셨어요?"
        elif "보고싶" in user_txt:
            reply = "저도 사장님 보고 싶었어요! 곁에서 항상 응원하고 있습니다💛"
        elif "고마워" in user_txt or "감사" in user_txt:
            reply = "항상 사장님께 감사드립니다! 도움이 되어드릴 수 있어 행복해요😊"
        elif "힘들" in user_txt or "지쳤" in user_txt or "속상" in user_txt:
            reply = "많이 힘드셨죠? 언제든 애순이가 사장님 곁을 지키고 있습니다. 파이팅입니다!"
        elif "피곤" in user_txt:
            reply = "많이 피곤하셨죠? 푹 쉬시고, 에너지 충전해서 내일도 힘내세요!"
        elif "졸려" in user_txt:
            reply = "졸릴 땐 잠깐 스트레칭! 건강도 꼭 챙기시고, 화이팅입니다~"
        elif "밥" in user_txt or "점심" in user_txt:
            reply = "아직 못 먹었어요! 사장님은 맛있게 드셨나요? 건강도 꼭 챙기세요!"
        elif "날씨" in user_txt:
            reply = "오늘 날씨 정말 좋네요! 산책 한 번 어떠세요?😊"
        elif "생일" in user_txt or "축하" in user_txt:
            reply = "생일 축하드립니다! 늘 행복과 건강이 가득하시길 바랍니다🎂"
        elif "화이팅" in user_txt or "파이팅" in user_txt:
            reply = "사장님, 항상 파이팅입니다! 힘내세요💪"
        elif "잘자" in user_txt or "굿나잇" in user_txt:
            reply = "좋은 꿈 꾸시고, 내일 더 힘찬 하루 보내세요! 잘 자요😊"
        elif "수고" in user_txt or "고생" in user_txt:
            reply = "사장님 오늘도 정말 수고 많으셨습니다! 항상 응원합니다💛"
        elif "재미있" in user_txt or "웃기" in user_txt:
            reply = "사장님이 웃으시면 애순이도 너무 좋아요! 앞으로 더 재미있게 해드릴게요😄"
        elif user_txt in ["애순", "애순아"]:
            reply = "안녕하세요, 사장님! 궁금하신 점 언제든 말씀해 주세요 😊"
        else:
            reply = "사장님! 애순이 항상 곁에 있어요😊 궁금한 건 뭐든 말씀해 주세요!"

        st.session_state.chat_log.append({
            "role": "bot",
            "content": reply,
            "display_type": "single_answer"
        })
        st.session_state.scroll_to_bottom_flag = True
        return

    # ↓↓↓ 이하 기존 Q&A 챗봇 처리 ↓↓↓
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

        # 매칭 5개 이상시 유도질문
        if len(matched) >= 5:
            main_word = question_input.strip()
            main_word = re.sub(r"[^가-힣a-zA-Z0-9]", "", main_word)
            if len(main_word) >= 1:
                st.session_state.pending_keyword = user_input
                st.session_state.chat_log.append({
                    "role": "bot",
                    "content": f"사장님, <b>{main_word}</b>의 어떤 부분이 궁금하신가요? 예) 한도, 결제, 사용방법 등 궁금한 점을 더 구체적으로 입력해 주세요!",
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
                # single_answer는 dict (q, a)
                if isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += (
                        '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                        f"<p style='margin-bottom: 8px;'><strong>질문:</strong> {q}</p>"
                        f"<p>👉 <strong>답변:</strong> {a}</p>"
                        '</div></div>'
                    )
                else:
                    # 애순 잡담 등 텍스트 응답
                    bot_answer = str(entry["content"]).replace("\n", "<br>")
                    chat_html_content += (
                        '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                        f"<p>🧾 <strong>답변:</strong><br>{bot_answer}</p>"
                        '</div></div>'
                    )
            elif entry.get("display_type") == "multi_answer":
                chat_html_content += "<div class='message-row bot-message-row'><div class='message-bubble bot-bubble'>"
                chat_html_content += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
                if isinstance(entry["content"], list):
                    for i, pair in enumerate(entry["content"]):
                        q = pair['q'].replace('\n', '<br>')
                        a = pair['a'].replace('\n', '<br>')
                        chat_html_content += f"""
                        <p class='chat-multi-item' style="margin-bottom: 10px;">
                            <strong>{i+1}. 질문:</strong> {q}<br>
                            👉 <strong>답변:</strong> {a}
                        </p>
                        """
                elif isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += f"""
                        <p class='chat-multi-item' style="margin-bottom: 10px;">
                            <strong>질문:</strong> {q}<br>
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
                bot_answer = str(entry["content"]).replace("\n", "<br>")
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
