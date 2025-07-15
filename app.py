import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import base64
import os
import re

st.markdown("""
<style>
/* 전체 앱 상단·하단 공백 최소화 */
.stApp {
    padding-top: 0px !important;
    margin-top: 0px !important;
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
    background-color: #fff;
}
/* 모든 컨테이너 및 블록 공백 축소 */
.block-container, .element-container, .stContainer, .stMarkdown, .stHeader, .stSubheader, .stTextInput, .stTextArea, .stButton {
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}
/* columns(이미지+인사말) 좌우 여백도 최소화 */
.stColumns {
    gap: 8px !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
}
/* 인사말 영역, 캐릭터 영역도 공란 최소 */
.intro-container {
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}
/* hr(구분선) 공란 최소 */
hr {
    margin-top: 2px !important;
    margin-bottom: 2px !important;
}
</style>
""", unsafe_allow_html=True)
# 1. [지점 설정 테이블]
BRANCH_CONFIG = {
    "gj":    {"bot_name": "은주",    "intro": "광주지점 이쁜이 ‘은주’입니다.❤️",    "image": "eunju_character.webp"},
    "dj":    {"bot_name": "소원",    "intro": "대전지점 이쁜이 ‘소원’입니다.❤️",    "image": "sowon_character.webp"},
    "cb":   {"bot_name": "현의",    "intro": "충북지점 엄마 ‘현의’입니다.❤️",    "image": "hyuni_character.webp"},
    "sc":   {"bot_name": "주희",    "intro": "순천지점 이쁜이 ‘주희’입니다❤️.",    "image": "juhee_character.webp"},
    "jj":     {"bot_name": "삼숙",    "intro": "전주지점 엄마 ‘삼숙’입니다.❤️",    "image": "samsook_character.webp"},
    "is":      {"bot_name": "수빈",    "intro": "익산지점 이쁜이 ‘수빈’입니다.❤️",    "image": "subin_character.webp"},
    "ca":    {"bot_name": "연지",    "intro": "천안지점 희망 ‘연지’입니다.❤️",    "image": "yeonji_character.webp"},
    "yd":     {"bot_name": "상민",    "intro": "예당지점 이쁜이 ‘상민’입니다.❤️",    "image": "sangmin_character.webp"},
    "djt2": {"bot_name": "영경",    "intro": "대전TC2지점 이쁜이 ‘영경’입니다.❤️", "image": "youngkyung_character.webp"},
    "ctc": {"bot_name": "유림",    "intro": "청주TC지점 이쁜이 ‘유림’입니다.❤️", "image": "youlim_character.webp"},
    "shj": {"bot_name": "혜련",    "intro": "안녕하세요~ 서청주지점 꽃 ‘혜련’이에요❤️", "image": "heryun_character.webp"},
    "default":    {"bot_name": "애순이",  "intro": "충청호남본부 매니저봇 ‘애순이’입니다.❤️", "image": "managerbot_character.webp"}
}

# 2. [지점 파라미터 추출]
branch = st.query_params.get('branch', ['default'])
branch = str(branch).lower() if branch and str(branch).lower() != "none" else "default"
config = BRANCH_CONFIG.get(branch, BRANCH_CONFIG["default"])

# 3. [캐릭터 이미지 불러오기]
def get_character_img_base64(img_path):
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
            return f"data:image/webp;base64,{b64}"
    return None

def get_intro_html():
    char_img = get_character_img_base64(config["image"])
    img_tag = f'<img src="{char_img}" width="75" style="margin-right:17px; border-radius:16px; border:1px solid #eee;">' if char_img else ''
    return f"""
    <div style="display: flex; align-items: flex-start; margin-bottom:18px;">
        {img_tag}
        <div>
            <h2 style='margin:0 0 8px 0;font-weight:900;'>사장님, 안녕하세요!</h2>
            <p>{config['intro']}</p>
            <p>저에게 오시기전에 <br>
            여기에서 먼저 물어봐 주세요! 궁금하신거 단어를 입력하시면 되여^*^<br>
            예를들면 자동차, 카드, 자동이체등...제가 아는 건 바로, 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
            늘 옆에서 든든하게 함께하겠습니다.</p>
            <strong>잘 부탁드려요! 😊</strong>
        </div>
    </div>
    """

# 4. [구글시트(공용) 연결]
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    # ★ 공용 질의응답시트 키만 아래에 넣으세요!
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# 5. [채팅 세션/로직/FAQ 등 기존 app.py와 동일하게 복붙]
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
        return f"사장님, {answer} <br> <strong>❤️궁금한거 해결되셨나요?!😊</strong>"

def handle_question(question_input):
    SIMILARITY_THRESHOLD = 0.3
    user_txt = question_input.strip().replace(" ", "").lower()
def handle_question(question_input):
    SIMILARITY_THRESHOLD = 0.3
    user_txt = question_input.strip().replace(" ", "").lower()

    # [1] 잡담/감정/상황 패턴(애순 없을 때도 무조건 반응)
    chit_chat_patterns = [
        (["사랑", "좋아해"], "사장님, 저도 사랑합니다! 💛 언제나 사장님 곁에 있을게요!"),
        (["잘지냈", "안녕"], "네! 사장님 덕분에 잘 지내고 있습니다😊 사장님은 잘 지내셨어요?"),
        (["보고싶"], "저도 사장님 보고 싶었어요! 곁에서 항상 응원하고 있습니다💛"),
        (["고마워", "감사"], "항상 사장님께 감사드립니다! 도움이 되어드릴 수 있어 행복해요😊"),
        (["힘들", "지쳤", "속상"], "많이 힘드셨죠? 언제든 제가 사장님 곁을 지키고 있습니다. 파이팅입니다!"),
        (["피곤"], "많이 피곤하셨죠? 푹 쉬시고, 에너지 충전해서 내일도 힘내세요!"),
        (["졸려"], "졸릴 땐 잠깐 스트레칭! 건강도 꼭 챙기시고, 화이팅입니다~"),
        (["밥", "점심", "식사"], "아직 못 먹었어요! 사장님은 맛있게 드셨나요? 건강도 꼭 챙기세요!"),
        (["날씨"], "오늘 날씨 정말 좋네요! 산책 한 번 어떠세요?😊"),
        (["생일", "축하"], "생일 축하드립니다! 늘 행복과 건강이 가득하시길 바랍니다🎂"),
        (["화이팅", "파이팅"], "사장님, 항상 파이팅입니다! 힘내세요💪"),
        (["잘자", "굿나잇"], "좋은 꿈 꾸시고, 내일 더 힘찬 하루 보내세요! 잘 자요😊"),
        (["수고", "고생"], "사장님 오늘도 정말 수고 많으셨습니다! 항상 응원합니다💛"),
        (["재미있", "웃기"], "사장님이 웃으시면 애순이도 너무 좋아요! 앞으로 더 재미있게 해드릴게요😄"),
    ]
    for keywords, reply in chit_chat_patterns:
        if any(kw in user_txt for kw in keywords):
            st.session_state.chat_log.append({
                "role": "user",
                "content": question_input,
                "display_type": "question"
            })
            st.session_state.chat_log.append({
                "role": "bot",
                "content": reply,
                "display_type": "single_answer"
            })
            st.session_state.scroll_to_bottom_flag = True
            return
# [2] "애순"이 들어간 인삿말 (기존 + return 추가)
    if "애순" in user_txt:
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })
        if user_txt in ["애순", "애순아"]:
            reply = "안녕하세요, 사장님! 궁금하신 점 언제든 말씀해 주세요 😊"
        else:
            reply = "사장님! 애순이 항상 곁에 있어요 😊 궁금한 건 뭐든 말씀해 주세요!"
        st.session_state.chat_log.append({
            "role": "bot",
            "content": reply,
            "display_type": "single_answer"
        })
        st.session_state.scroll_to_bottom_flag = True
        return

    # [3] 각 지점 캐릭터 이름(bot_name)도 반응하게 처리
    bot_names = [v["bot_name"] for k, v in BRANCH_CONFIG.items()]
    for bot_name in bot_names:
        if bot_name in user_txt:
            st.session_state.chat_log.append({
                "role": "user",
                "content": question_input,
                "display_type": "question"
            })
            reply = f"안녕하세요, 사장님! 저는 항상 곁에 있는 {bot_name}입니다 😊 궁금한 건 뭐든 말씀해 주세요!"
            st.session_state.chat_log.append({
                "role": "bot",
                "content": reply,
                "display_type": "single_answer"
            })
            st.session_state.scroll_to_bottom_flag = True
            return

    # ↓↓↓ Q&A 챗봇 처리 ↓↓↓
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
                    "content": f"사장님, <b>{main_word}</b>의 어떤 부분이 궁금하신가요? 유사한 질문이 너무 많아요~ 궁금한 점을 좀 더 구체적으로 입력해 주세요!",
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
            # [3] 답변이 아예 없을 때 안내멘트
            st.session_state.chat_log.append({
                "role": "bot",
                "content": "사장님~~ 음~ 답변이 준비 안된 질문이에요. 진짜 궁금한거로 말씀해 주세요^*^",
                "display_type": "single_answer"
            })
            st.session_state.scroll_to_bottom_flag = True
            return
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
                if isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += (
                        '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                        f"<p style='margin-bottom: 8px;'><strong style='color:#003399;'>질문: {q}</strong></p>"
                        f"<p>👉 <strong>답변:</strong> {a}</p>"
                        '</div></div>'
                    )
                else:
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
                            <strong style="color:#003399;">{i+1}. 질문: {q}</strong><br>
                            👉 <strong>답변:</strong> {a}
                        </p>
                        """
                elif isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += f"""
                        <p class='chat-multi-item' style="margin-bottom: 10px;">
                            <strong style="color:#003399;">{i+1}. 질문: {q}</strong><br>
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
