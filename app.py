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
/* 1. 챗 말풍선 텍스트 자동 색상 지정 */
.message-bubble p, .message-bubble strong {
    color: inherit !important;
}

/* 2. 다크모드에서는 흰색 계열로 자동 지정 */
@media (prefers-color-scheme: dark) {
    html, body, .stApp {
        background-color: #1a1a1a !important;
        color: #eeeeee !important;
    }

    .message-bubble p, .message-bubble strong {
        color: #eeeeee !important; /* 이 부분 추가 */
    }

    .intro-bubble h2, .intro-bubble p {
        color: #eeeeee !important; /* 이 부분 추가 */
    }

    .bot-bubble, .user-bubble, .intro-bubble, .message-bubble {
        color: #eeeeee !important;
    }

    input[type="text"], textarea {
        background-color: #333 !important;
        color: #fff !important;
        border: 1px solid #666 !important;
    }

    ::placeholder {
        color: #bbb !important;
    }

    .input-form-fixed {
        background-color: #1A1A1A !important;
        box-shadow: 0 -2px 16px rgba(255,255,255,0.05) !important;
    }

    #speech_status {
        color: #ccc !important;
    }
}

/* 3. 라이트모드는 기존대로 유지 */
@media (prefers-color-scheme: light) {
    html, body, .stApp {
        background-color: #ffffff !important;
        color: #111 !important;
    }

    .message-bubble p, .message-bubble strong {
        color: #111 !important;
    }

    .intro-bubble h2, .intro-bubble p {
        color: #111 !important;
    }

    input[type="text"], textarea {
        background-color: #fff !important;
        color: #000 !important;
        border: 1px solid #ccc !important;
    }

    ::placeholder {
        color: #888 !important;
    }

    .input-form-fixed {
        background-color: #fff !important;
        box-shadow: 0 -2px 16px rgba(0,0,0,0.05) !important;
    }

    #speech_status {
        color: #444 !important;
    }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<style>
/* 전체 앱 상단·하단 공백 최소화 */
.stApp {
    padding-top: 5px !important;
    margin-top: 0px !important;
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
    background-color: #fff;
}
/* 모든 컨테이너 및 블록 공백 축소 */
.block-container, .element-container, .stContainer, .stMarkdown, .stHeader, .stSubheader, .stTextInput, .stTextArea, .stButton {
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding-top: 5px !important;
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
    "dt2": {"bot_name": "영경",    "intro": "대전TC2지점 이쁜이 ‘영경’입니다.❤️", "image": "youngkyung_character.webp"},
    "ctc": {"bot_name": "유림",    "intro": "청주TC지점 이쁜이 ‘유림’입니다.❤️", "image": "youlim_character.webp"},
    "scj": {"bot_name": "혜련",    "intro": "서청주지점 꽃 ‘혜련’이에요❤️", "image": "heryun_character.webp"},
    "yst": {"bot_name": "영주",    "intro": "유성TC지점 이쁜이 ‘영주’에요❤️", "image": "youngju_character.webp"},
    "gs": {"bot_name": "혜진",    "intro": "군산지점 이쁜이 ‘’혜진이에요❤️", "image": "hejin_character.webp"},
    "ds": {"bot_name": "소정",    "intro": "둔산지점 이쁜이 ‘’소정이에요❤️", "image": "sojung_character.webp"},
    "scjj": {"bot_name": "지영",    "intro": "순천중앙지점 이쁜이 ‘’지영이에요❤️", "image": "jiyoung_character.webp"},
    "smj": {"bot_name": "서희",    "intro": "상무지점 이쁜이 ‘’서희이에요❤️", "image": "seohi_character.webp"},
    "cjj": {"bot_name": "윤희",    "intro": "충주지점 이쁜이 ‘’윤희에요❤️", "image": "yunhi_character.webp"},
    "ns": {"bot_name": "세정",    "intro": "논산지점 이쁜이 ‘’세정이에요❤️", "image": "sejung_character.webp"},
    "sjj": {"bot_name": "효인",    "intro": "세종지점 이쁜 ‘’효인이에요❤️", "image": "hyoin_character.webp"},
    "default":    {"bot_name": "애순이",  "intro": "충청호남본부 도우미 ‘애순이’에요.❤️", "image": "managerbot_character.webp"}
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
    default_img_path = BRANCH_CONFIG["default"]["image"]
    if os.path.exists(default_img_path):
        with open(default_img_path, "rb") as img_file:
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
            <h2 style='margin:0 0 8px 0;font-weight:700;'>사장님, 안녕하세요!!</h2>
            <p style="font-weight: 700;">{config['intro']}</p>
            <p>궁금하신거 있으시면 <br>
            여기에서 먼저 물어봐 주세요! <br>
            궁금하신 내용을 입력하시면 되여~</p>
            <p>예를들면 자동차, 카드등록, 자동이체등...<br>
            제가 아는 건 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록
            늘 옆에서 제가 함께하겠습니다.</p>
            <p style="font-weight:700; color:#d32f2f !important; font-size:1.15em; font-family:'궁서', 'Gungsuh', serif;">
    유지율도 조금만 더 챙겨주실거죠? 사랑해요~~^*^😊
</p>

            <strong style="font-weight:900; color:#003399;">사장님!! 오늘도 화이팅!!!</strong>
        </div>
    </div>
    """

# 4. [구글시트(공용) 연결]
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    import json

    json_key_dict = json.loads(st.secrets["gcp_service_account"])
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
    text = re.sub(r"(시|요|가요|인가요|하나요|할까요|할게요|하죠|할래요|습니까|나요|지요|죠|죠요|되나요|되었나요|되니)$", "", text.lower())
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", text)
def extract_keywords(text):
    stopwords = [
        
    "이", "가", "은", "는", "을", "를", "에", "의", "로", "으로", "도", "만", "께", "에서", "하고", "보다", "부터", "까지", "와", "과",
    "요", "해요", "했어요", "합니다", "해주세요", "해줘요", "하기", "할게요", "됐어요", "할래요",
    "어떻게", "어떡해", "방법", "알려줘", "알려줘요", "알려주세요", "무엇", "무엇인가요", "뭐", "뭔가요", "뭔데요", "뭡니까",
    "도와줘", "도와줘요", "하나요", "하는법", "되나요", "인가요", "있나요", "되었나요", "있습니까", "하나", "진행하나요", "되니", "되냐", "하냐"
]
    text = re.sub(r"[^가-힣a-zA-Z0-9]", " ", text.lower())
    words = [normalize_text(w) for w in text.split() if w not in stopwords and len(w) > 1]
    # words = [w for w in text.split() if w not in stopwords]
    return words

def add_friendly_prefix(answer):
    answer = answer.strip()
    if answer[:7].replace(" ", "").startswith("사장님"):
        return answer
    else:
        return f"사장님, {answer} <br> <strong>❤️궁금한거 해결되셨나요?!😊</strong>"

def handle_question(question_input):
    SIMILARITY_THRESHOLD = 0.7
    user_txt = question_input.strip().replace(" ", "").lower()

# ✅ [1단계 추가] 이전에 남아있는 pending_keyword 강제 초기화 (질문 바뀐 경우)
    if st.session_state.pending_keyword:
        prev = normalize_text(st.session_state.pending_keyword)
        now = normalize_text(question_input)
        if prev != now:
            st.session_state.pending_keyword = None

    # [1] 잡담/감정/상황 패턴(애순 없을 때도 무조건 반응)
    chit_chat_patterns = [
        (["사랑", "좋아해"], "사장님, 저도 사랑합니다! 💛 언제나 사장님 곁에 있을게요!"),
        (["잘지", "안녕"], "네! 안녕하세요!!😊 사장님~ 오늘은 기분 좋으시죠?"),
        (["보고"], "저도 사장님 보고 싶었어요! 곁에서 항상 응원하고 있습니다💛"),
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
        q_input_keywords = extract_keywords(user_input)

        matched = []
        # ✅ [2단계 추가] 이전에 남은 keyword가 있고, 이번에 매칭이 충분하지 않으면 초기화
        if st.session_state.pending_keyword:
            st.session_state.pending_keyword = None
        
        for r in records:
            sheet_q_norm = normalize_text(r["질문"])
            sheet_keywords = extract_keywords(r["질문"])

            # 1) 핵심 키워드가 최소 1개 이상 겹치면 매칭
            match_score = sum(1 for kw in q_input_keywords if kw in sheet_keywords)
            sim_score = get_similarity_score(q_input_norm, sheet_q_norm)
            total_score = (match_score * 1.5) + (sim_score * 1.0)
            
            # 단, 핵심 키워드가 없을 땐 유사도/포함 매칭 제외 (오매칭 방지)
            if match_score >= 1 or sim_score >= 0.45:
                matched.append((total_score, r))
        matched.sort(key=lambda x: x[0], reverse=True)
        seen_questions = set()
        unique_matched = []
        for score, r in matched:
            if r["질문"] not in seen_questions:
                unique_matched.append((score, r))
                seen_questions.add(r["질문"])
        matched = unique_matched
        
        if q_input_keywords:
            keyword_norm = normalize_text(q_input_keywords[0])
            top_matches = [r for _, r in matched if keyword_norm in extract_text(r["질문"])]
            if not top_matches:
                top_matches = [r for _, r in matched[:4]]
            else:
                top_matches = top_matches[:10]
        else:
            top_matches = [r for _, r in matched[:4]]
        
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        # 매칭 5개 이상시 유도질문
        if len(top_matches) >= 5:
            main_word = question_input.strip()
            main_word = re.sub(r"[^가-힣a-zA-Z0-9]", "", main_word)
            
            example_pairs = [(m["질문"], add_friendly_prefix(m["답변"])) for m in top_matches[:5]]
            examples_html = "".join([
                f"""
                <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                     <strong style="color:#003399;">질문) {q}</strong><br>
                     
                    👉 <strong>답변:</strong> {a}
                </div>
                """
                
                for q, a in example_pairs
            ])


            st.session_state.pending_keyword = user_input
            st.session_state.chat_log.append({
                "role": "bot",
                "content": (
                    "<div class='example-guide-block'>"
                    f"<span class='example-guide-title'>사장님, <b>{main_word}</b>의 어떤 부분이 궁금하신가요?</span>"
                    " 유사한 질문이 너무 많아요~ 궁금한 점을 좀 더 구체적으로 입력해 주세요!<br>"
                    "<span class='example-guide-emph'><b>아래처럼 다시 물어보시면 바로 답변드릴 수 있어요.</b></span><br>"
                    f"{examples_html}"
                    "</div>"
                    """
                    <style>
                    .example-guide-block {
                        margin: 10px 0 0 0;
                        font-size: 1.05em;
                    }
                    .example-guide-title {
                        color: #226ed8;
                        font-weight: 700;
                    }
                    .example-guide-emph {
                        color: #d32f2f;
                        font-weight: 700;
                    }
                    .example-item {
                        margin-top: 9px;
                        margin-bottom: 2px;
                        padding-left: 10px;
                        line-height: 1.5;
                        border-left: 3px solid #e3e3e3;
                        background: #f9fafb;
                        border-radius: 5px;
                        font-size: 0.98em;
                    }
                    @media (prefers-color-scheme: dark) {
                        .example-guide-title { color: #64b5f6; }
                        .example-guide-emph { color: #ffab91; }
                        .example-item {
                            background: #232c3a;
                            border-left: 3px solid #374151;
                            color: #eaeaea;
                        }
                    }
                    </style>
                    """
                ),
                "display_type": "pending"
            })
            st.session_state.scroll_to_bottom_flag = True
            return


        if len(top_matches) == 1:
            bot_answer_content = {
                "q": top_matches[0]["질문"],
                "a": add_friendly_prefix(top_matches[0]["답변"])
            }
            bot_display_type = "single_answer"
        elif 2 <= len(top_matches) <= 4:
            bot_answer_content = []
            for r in top_matches:
                bot_answer_content.append({
                    "q": r["질문"],
                    "a": add_friendly_prefix(r["답변"])
                })
            bot_display_type = "multi_answer"
        elif len(top_matches) == 0:
            # [3] 답변이 아예 없을 때 안내멘트
            st.session_state.chat_log.append({
                "role": "bot",
                "content": "사장님~~죄송해요.. 아직 준비가 안된 질문이에요. 이 부분은 매니저에게 개별 문의 부탁드려요^*^~",
                "display_type": "single_answer"
            })
            st.session_state.scroll_to_bottom_flag = True
            return
        if len(top_matches) > 0:
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
                'style="background:#dcf8c6;font-weight:700;'
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
                        <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                            <strong style="color:#003399;">{i+1}. 질문: {q}</strong><br>
                            👉 <strong>답변:</strong> {a}
                        </div>
                        """
                elif isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += f"""
                        <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                            <strong style="color:#003399;">질문: {q}</strong><br>
                            👉 <strong>답변:</strong> {a}
                        </div>
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
# === 여기서부터 추가 ===
    chat_style = """
<style id="dynamic-color-style">
.message-row, .message-bubble, .bot-bubble, .intro-bubble,
.message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p {
    color: #111 !important;
}
.user-bubble, .user-bubble p {
    color: #111 !important;
}
</style>
<script>
function updateColorMode() {
    var isDark = false;
    try {
        isDark = window.parent.matchMedia && window.parent.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch(e) {}
    var styleTag = document.getElementById('dynamic-color-style');
    if (isDark) {
        styleTag.innerHTML = 
.message-row, .message-bubble, .bot-bubble, .intro-bubble, .message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p { color: #eeeeee !important; }
.user-bubble, .user-bubble p { color: #111 !important; }
;
    } else {
        styleTag.innerHTML = 
.message-row, .message-bubble, .bot-bubble, .intro-bubble, .message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p { color: #111 !important; }
.user-bubble, .user-bubble p { color: #111 !important; }
;
    }
}
updateColorMode();
if (window.parent.matchMedia) {
    window.parent.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateColorMode);
}
</script>
"""
    return f"""
    {chat_style}
    <div id="chat-content-scroll-area">
        {chat_html_content}
        <div id="chat-scroll-anchor"></div>
    </div>
    {scroll_iframe_script}
    """

components.html(
    display_chat_html_content(),
    height=400,
    scrolling=True
)

st.markdown("""
<style>
button[kind="secondaryFormSubmit"] {
    background: #238636 !important;
    color: #fff !important;
    border-radius: 6px !important;
    border: none !important;
    font-weight: bold !important;
    font-family: 'Nanum Gothic', 'Arial', sans-serif !important;
    font-size: 16px !important;
    padding: 4px 16px !important;
    height: 34px !important;
    min-width: 72px !important;
    box-shadow: none !important;
}

button[kind="secondaryFormSubmit"]:hover {
    background: #008000 !important;
    color: #ffeb3b !important;
}
</style>
""", unsafe_allow_html=True)

 # 2. 음성인식 버튼
components.html("""
<style>
#voice-block {
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
}

#toggleRecord {
    background: #238636;
    color: #fff;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    padding: 6px 16px;
    box-shadow: 0 2px 8px rgba(0,64,0,0.10);
    font-family: 'Nanum Gothic', 'Arial', sans-serif;
    cursor: pointer;
    transition: all 0.3s ease;
    height: 36px;
    min-width: 80px;
    margin-bottom: 2px;
}

#toggleRecord:hover {
    background: #008000;
    color: #ffeb3b;
}

#speech_status {
    font-size: 0.85em;
    color: #1b5e20;
    margin-left: 4px;
    display: none;  /* 처음엔 숨김 */
}
</style>

<div id="voice-block">
    <button id="toggleRecord">🎤 음성</button>
    <div id="speech_status"></div>
</div>

<script>
let isRecording = false;
let recognition;

document.getElementById("toggleRecord").addEventListener("click", function () {
    const input = window.parent.document.querySelector('textarea, input[type=text]');
    const status = document.getElementById("speech_status");

    if (input) input.focus();
    if (!isRecording) {
        recognition = new webkitSpeechRecognition();
        recognition.lang = "ko-KR";
        recognition.interimResults = false;
        recognition.continuous = true;

        recognition.onresult = function (event) {
            let fullTranscript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                fullTranscript += event.results[i][0].transcript;
            }
            const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            setter.call(input, fullTranscript);
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.focus();
            status.style.display = "inline";
            status.innerText = "🎤 음성 입력 중!";
        };

        recognition.onerror = function (e) {
            status.style.display = "inline";
            status.innerText = "⚠️ 오류 발생: " + e.error;
            isRecording = false;
            document.getElementById("toggleRecord").innerText = "🎤 음성";
        };

        recognition.onend = function () {
            isRecording = false;
            document.getElementById("toggleRecord").innerText = "🎤 음성";
            status.style.display = "inline";
            status.innerText = "🛑 음성 인식 종료되었습니다.";
        };

        recognition.start();
        isRecording = true;
        document.getElementById("toggleRecord").innerText = "🛑 멈추기";
        status.style.display = "inline";
        status.innerText = "🎤 음성 입력을 시작합니다.";
    } else {
        recognition.stop();
        isRecording = false;
        document.getElementById("toggleRecord").innerText = "🎤 음성";
        status.style.display = "inline";
        status.innerText = "🛑 음성 인식 종료되었습니다.";
    }
});
</script>
""", height=45)

with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("Enter")
    if submitted and question_input:
        handle_question(question_input)
        st.rerun()


st.markdown("""
<style>
/* 모바일에서 입력창 하단 고정 및 키보드 위로 올리기 */
.input-form-fixed {
    position: fixed !important;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
    background: #fff;
    box-shadow: 0 -2px 16px rgba(0,0,0,0.07);
    padding: 14px 8px 14px 8px;
}
@media (max-width: 600px) {
    .input-form-fixed { padding-bottom: 16px !important; }
}
</style>
<script>
// 모바일에서 키보드 올라올 때 입력창 자동 스크롤
window.addEventListener('focusin', function(e) {
    var el = document.querySelector('.input-form-fixed');
    if (el) {
        setTimeout(function() {
            el.scrollIntoView({behavior: 'smooth', block: 'end'});
        }, 300);
    }
});
</script>
""", unsafe_allow_html=True) 