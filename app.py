def get_auto_faq_list():
    try:
        rows = get_sheet_records()  # ✅ 캐시 사용
        qs = [str(r.get("질문","")).strip() for r in rows if r.get("질문")]
        if not qs:
            return []

        KEYWORDS = ("카드", "구비서류", "자동차", "자동이체", "계약자 변경")
        cand = [q for q in qs if len(q) <= 25 and any(k in q for k in KEYWORDS)]

        from collections import Counter
        freq = Counter(cand)

        # 중복 제거(첫 등장 순서 유지)
        seen, uniq = set(), []
        for q in cand:
            if q not in seen:
                seen.add(q)
                uniq.append(q)

        # 빈도(내림차순) → 길이(오름차순)로 정렬하여 상위 5개
        uniq.sort(key=lambda q: (-freq[q], len(q)))
        return uniq[:5]
    except Exception:
        return []


import time
from datetime import datetime
import pytz
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components
import difflib
import base64
import os
import re
import json
import hashlib  # ✅ 중복 방지용 시그니처 생성

GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _load_sa_info():
    raw = st.secrets.get("gcp_service_account")
    if raw is None:
        raise RuntimeError("st.secrets['gcp_service_account'] 가 없습니다.")
    return json.loads(raw) if isinstance(raw, str) else raw

@st.cache_resource(show_spinner=False)
def _get_gsheet_client():
    sa_info = _load_sa_info()
    creds = Credentials.from_service_account_info(sa_info, scopes=GOOGLE_SCOPES)
    return gspread.authorize(creds)

DEDUPE_WINDOW_SEC = 6  # 같은 입력이 N초 안에 또 오면 중복으로 간주

def _make_submit_sig(text: str, branch: str) -> str:
    """질문 + 지점으로 고유 시그니처 생성"""
    base = f"{(branch or '').strip()}|{(text or '').strip()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def is_duplicate_submit(text: str, branch: str) -> bool:
    """최근 제출과 동일하면 True, 아니면 False(그리고 최신 제출로 기록)"""
    sig = _make_submit_sig(text, branch)
    now = time.time()
    last_sig = st.session_state.get("last_submit_sig")
    last_ts  = st.session_state.get("last_submit_ts", 0.0)

    if last_sig == sig and (now - last_ts) < DEDUPE_WINDOW_SEC:
        return True  # 🚫 중복

    # 최신 제출로 갱신
    st.session_state["last_submit_sig"] = sig
    st.session_state["last_submit_ts"]  = now
    return False

def append_log_row_to_logs(row: list):
    """
    row 예시: [date, time, branch, question]
    """
    gc = _get_gsheet_client()
    sh = gc.open_by_key(st.secrets["LOG_SHEET_KEY"])
    try:
        ws = sh.worksheet("logs")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="logs", rows=1000, cols=10)
        ws.append_row(["date", "time", "branch", "question"], value_input_option="USER_ENTERED")
    ws.append_row(row, value_input_option="USER_ENTERED")

def get_branch_param() -> str:
    # Streamlit 버전별로 안전하게 branch 파라미터 읽기
    try:
        return (st.query_params.get("branch") or "").strip()
    except:
        try:
            return st.experimental_get_query_params().get("branch", [""])[0].strip()
        except:
            return ""

st.set_page_config(layout="wide")
# === URL 하드리셋(hardreset=1) 감지: 세션 초기화 후 첫 화면으로 ===
# === 세션 하드 리셋 ===
def _hard_reset():
    st.session_state.clear()  # chat_log, pending_keyword 등 초기화
    st.rerun()                # 첫 화면으로 다시 렌더

def _qp_to_dict():
    try:
        d = dict(st.query_params)
    except Exception:
        d = st.experimental_get_query_params()
    # list -> scalar 평탄화
    return {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in d.items()}

_qp = _qp_to_dict()
if _qp.get("hardreset") == "1":
    st.session_state.clear()  # 인사말만 보이는 상태로 초기화
    _qp.pop("hardreset", None)
    _qp["ts"] = str(int(time.time()))  # 캐시 무력화용
    try:
        st.query_params.clear()
        st.query_params.update(_qp)
    except Exception:
        st.experimental_set_query_params(**_qp)
    st.rerun()

st.markdown("""
<style>
/* 데스크탑에서 전체 본문 컨테이너 폭을 통일 */
@media (min-width:1100px){
  /* 1) Streamlit 메인 컨테이너를 900px로 고정 + 중앙정렬 */
  .block-container{
    max-width:900px !important;
    margin-left:auto !important;
    margin-right:auto !important;
  }
  /* 2) 입력 폼/텍스트박스도 부모 폭에 맞춰 100% */
  form[data-testid="stForm"],
  [data-testid="stTextInputRootElement"],
  [data-testid="stTextAreaRootElement"]{
    width:100% !important;
    max-width:900px !important;
    margin-left:auto !important;
    margin-right:auto !important;
  }
  /* 3) iframe(인트로/음성)도 부모 폭(=900px)을 꽉 채우기 */
  div[data-testid="stIFrame"], 
  div[data-testid="stIFrame"] > iframe{
    width:100% !important;
  }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* HTML 컴포넌트(iframe) 래퍼와 iframe 자체를 전체폭으로 강제 */
div[data-testid="stIFrame"] { width: 100% !important; }
div[data-testid="stIFrame"] > iframe { width: 100% !important; }

/* 혹시 브라우저/버전 따라 data-testid가 달리 잡히는 경우를 대비한 보강 */
.element-container:has(> iframe) { width: 100% !important; max-width: 100% !important; }
iframe { width: 100% !important; }
</style>
""", unsafe_allow_html=True)
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
    "cb":   {"bot_name": "현의",    "intro": "음성의 희망 ‘현의’입니다.❤️",    "image": "hyuni_character.webp"},
    "cb1":   {"bot_name": "보라",    "intro": "제천의 희망 ‘보라’입니다.❤️",    "image": "bora_character.webp"},
    "sc":   {"bot_name": "주희",    "intro": "순천지점 이쁜이 ‘주희’입니다❤️.",    "image": "juhee_character.webp"},
    "jj":     {"bot_name": "삼숙",    "intro": "전주지점의 희망 ‘삼숙’입니다.❤️",    "image": "samsook_character.webp"},
    "is":      {"bot_name": "수빈",    "intro": "익산지점 이쁜이 ‘수빈’입니다.❤️",    "image": "subin_character.webp"},
    "ca":    {"bot_name": "연지",    "intro": "천안지점의 꽃 ‘연지’입니다.❤️",    "image": "yeonji_character.webp"},
    "yd":     {"bot_name": "상민",    "intro": "예당지점 이쁜이 ‘상민’입니다.❤️",    "image": "sangmin_character.webp"},
    "dt2": {"bot_name": "영경",    "intro": "대전TC2지점 이쁜이 ‘영경’입니다.❤️", "image": "youngkyung_character.webp"},
    "ctc": {"bot_name": "유림",    "intro": "청주TC지점 이쁜이 ‘유림’입니다.❤️", "image": "youlim_character.webp"},
    "scj": {"bot_name": "혜련",    "intro": "서청주지점 꽃 ‘혜련’이에요❤️", "image": "heryun_character.webp"},
    "yst": {"bot_name": "영주",    "intro": "유성TC지점 이쁜이 ‘영주’에요❤️", "image": "youngju_character.webp"},
    "gs": {"bot_name": "혜진",    "intro": "군산지점 이쁜이 혜진이에요❤️", "image": "hejin_character.webp"},
    "ds": {"bot_name": "소정",    "intro": "둔산지점 이쁜이 소정이에요❤️", "image": "sojung_character.webp"},
    "scjj": {"bot_name": "지영",    "intro": "순천중앙지점 이쁜이 지영이에요❤️", "image": "jiyoung_character.webp"},
    "smj": {"bot_name": "서희",    "intro": "상무지점 이쁜이 서희이에요❤️", "image": "seohi_character.webp"},
    "cjj": {"bot_name": "윤희",    "intro": "충주지점 이쁜이 윤희에요❤️", "image": "yunhi_character.webp"},
    "ns": {"bot_name": "세정",    "intro": "논산지점 이쁜이 세정이에요❤️", "image": "sejung_character.webp"},
    "sjj": {"bot_name": "효인",    "intro": "세종TC지점 이쁜 효인이에요❤️", "image": "hyoin_character.webp"},
    "mpj": {"bot_name": "아름",    "intro": "목포지점 이쁜이 아름이에요❤️", "image": "arum_character.webp"},
    "gjj": {"bot_name": "상아",    "intro": "광주중앙의 이쁜이 상아에요❤️", "image": "sanga_character.webp"},
    "mdj": {"bot_name": "정아",    "intro": "무등지점의 꽃 정아에요❤️", "image": "junga_character.webp"},
    "br": {"bot_name": "윤희",    "intro": "보령지점의 꽃 윤희에요❤️", "image": "yunhi1_character.webp"},
    "gr": {"bot_name": "혜진",    "intro": "계룡지점의 꽃 혜진에요❤️", "image": "hyejin_character.webp"},
    "as": {"bot_name": "규희",    "intro": "아산지점의 꽃 규희에요❤️", "image": "kyuhi_character.webp"},
    "dst": {"bot_name": "나라",    "intro": "둔산TC지점의 꽃 나라에요❤️", "image": "nara_character.webp"},
    "na": {"bot_name": "진선",    "intro": "남악지점의 꽃 진선이에요❤️", "image": "jinsun_character.webp"},
    "ssj": {"bot_name": "은정",    "intro": "서산지점의 꽃 은정이에요❤️", "image": "eunjung_character.webp"},
    "ssj1": {"bot_name": "수연",    "intro": "홍성의 꽃 수연에요❤️", "image": "suyun_character.webp"},
    "dh":   {"bot_name": "태연",    "intro": "대흥지점의 꽃 ‘태연’이예요.❤️",  "image": "taeyeon_character.webp"},
    "jnj":   {"bot_name": "민경",    "intro": "고흥의 꽃 ‘민경’이예요.❤️",  "image": "minkung_character.webp"},
    "jnj1":   {"bot_name": "호정",    "intro": "여수의 꽃 ‘호정’이예요.❤️",  "image": "hojung_character.webp"},
    "isj":   {"bot_name": "지혜",    "intro": "익산중앙지점의 꽃 ‘지혜’랍니다.❤️",  "image": "jihye_character.webp"},
    "bg":   {"bot_name": "시영",    "intro": "빛고을지점의 꽃 ‘시영’이예요.❤️",  "image": "siyoung_character.webp"},
    "caj":   {"bot_name": "지원",    "intro": "천안제일의 꽃 ‘지원’이예요.❤️",  "image": "jiwon_character.webp"},
    "dmj":   {"bot_name": "은채",    "intro": "미래지점의 꽃 ‘은채’예요.❤️",  "image": "enchae_character.webp"},
    "cat":   {"bot_name": "지현",    "intro": "천안TC지점의 꽃 ‘지현’이예요.❤️",  "image": "jiheon_character.webp"},
    "mpt2":   {"bot_name": "정옥",    "intro": "목포 TC2 지점의 꽃 ‘정옥’이예요.❤️",  "image": "jungok_character.webp"},
    "ma":   {"bot_name": "진남",    "intro": "모악지점의 꽃 ‘진남’이예요.❤️",  "image": "jinnam_character.webp"},
    "sgs":   {"bot_name": "은선",    "intro": "새군산지점의 꽃 ‘은선’이예요.❤️",  "image": "ensun_character.webp"},
    "jb":   {"bot_name": "현숙",    "intro": "전북지점의 꽃 ‘현숙’이예요.❤️",  "image": "hunsuk_character.webp"},
    "gst":   {"bot_name": "그라미",    "intro": "광주TC지점의 꽃 ‘그라미’ 예요.❤️",  "image": "grami_character.webp"},
    "dt1":   {"bot_name": "태연",    "intro": "대전TC1지점의 꽃 ‘태연’이예요.❤️",  "image": "taeyeon1_character.webp"},
    "mpt1":   {"bot_name": "지영",    "intro": "목포TC1지점의 꽃 ‘지영’이예요.❤️",  "image": "jiyoung1_character.webp"},
    "cjjj":   {"bot_name": "희정",    "intro": "청주제일지점의 꽃 ‘희정’이예요.❤️",  "image": "hijung_character.webp"},
    "chj":   {"bot_name": "소영",    "intro": "청주지점의 꽃 ‘소영’이예요.❤️",  "image": "soyoung_character.webp"},
    "default":    {"bot_name": "애순이",  "intro": "충청호남본부 도우미 ‘애순이’에요.❤️", "image": "managerbot_character.webp"}
}


# 2. [지점 파라미터 추출]
branch = get_branch_param() or "default"   # 이미 위에 정의된 안전한 함수 활용
branch = branch.lower()
config = BRANCH_CONFIG.get(branch, BRANCH_CONFIG["default"])

# 3. [캐릭터 이미지 불러오기]
@st.cache_data(show_spinner=False)
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
    
    faq_items = get_auto_faq_list()
    faq_inner = "".join([f"<li style='margin:4px 0;'>📌 {q}</li>" for q in faq_items])
    faq_block = f"""
        <details style='margin-top:14px; font-size:1em;'>
            <summary style='cursor:pointer; font-weight:bold; color:#d32f2f;'>📌 자주 묻는 질문 🔍</summary>
            <ul style='padding-left:20px; margin-top:8px;'>
                {faq_inner}
            </ul>
        </details>
    """ if faq_items else ""
    

    return f"""
    <div style="display:flex; align-items:flex-start; margin-bottom:18px; width:100%;">
        {img_tag}
        <div style="flex:1; min-width:0;">
       
            <h2 style='margin:0 0 8px 0;font-weight:700;'>사장님, 안녕하세요!!</h2>
            <p style="font-weight: 700;">{config['intro']}</p>
            <p>궁금하신 내용은 여기 <strong>애순이</strong>에게 먼저 물어봐 주세요!<br></p>
            <p>예를들면 자동차, 카드등록, 자동이체등...<br></p>
            <p>사장님들이 더 편하게 영업하실 수 있도록 늘 함께할께요~~</p>
            <p style="font-weight:700; color:#d32f2f !important; font-size:1.15em; font-family:'궁서', 'Gungsuh', serif;">
    유지율도 조금만 더 챙겨주실거죠? 사랑합니다~~^*^😊
</p>

            <strong style="font-weight:900; color:#003399;">사장님!! 오늘도 화이팅!!!</strong>
            {faq_block} 
        </div>
    </div>
    """

# 4. [구글시트(공용) 연결]
sheet = None
try:
    gc = _get_gsheet_client()
    # ★ 공용 질의응답시트 키만 아래에 넣으세요!
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")
# === 캐시: 시트 레코드 읽기 ===

@st.cache_data(ttl=60, show_spinner=False)
def get_sheet_records_cached():
    """시트 전체 레코드 캐시(60초). sheet가 없으면 빈 리스트."""
    try:
        if sheet is None:
            return []
        return sheet.get_all_records()
    except Exception:
        # API 일시 오류 등은 조용히 빈 리스트 반환
        return []

def get_sheet_records():
    """캐시 우선, 비정상 시 빈 리스트."""
    return get_sheet_records_cached()

@st.cache_data(ttl=60, show_spinner=False)
def build_qa_index(rows: list):
    indexed = []
    inverted = {}
    df_count = {}  # 문서 빈도

    for i, r in enumerate(rows):
        q_raw = str(r.get("질문", "")).strip()
        q_norm = normalize_text(q_raw)
        kset   = set(extract_keywords(q_raw))
        indexed.append({"row": r, "q_norm": q_norm, "kwords": kset})
        for tok in kset:
            if not tok:
                continue
            inverted.setdefault(tok, []).append(i)
            df_count[tok] = df_count.get(tok, 0) + 1

    # IDF 계산 (log 스무딩)
    import math
    N = max(1, len(indexed))
    idf = {tok: math.log((N + 1) / (df + 1)) + 1.0 for tok, df in df_count.items()}  # ≥ 1.0

    return indexed, inverted, idf

def get_qa_index():
    rows = get_sheet_records()
    return build_qa_index(rows)


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
    text = text.lower()
    
    text = re.sub(r"\b([가-힣]{2,10})(은|는|이|가|을|를|에|의|로|으로|도|만|께|에서|까지|보다|부터|한테|에게|하고|와|과)\b", r"\1", text)
    text = re.sub(r"(시|요|가요|인가요|하나요|할까요|할게요|하죠|할래요|습니까|나요|지요|죠|죠요|되나요|되었나요|되니)$", "", text)
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", text)

def extract_keywords(text):
    stopwords = [
        "이","가","은","는","을","를","에","의","로","으로","도","만","께","에서","부터","까지","보다","와","과","하고","한테","에게",
        "요","해요","했어요","합니다","해주세요","해줘요","하기","할게요","됐어요","할래요",
        "어떻게","방법","알려줘","무엇","뭐","도와줘","하나요","되나요","인가요","되었나요","하나","진행하나요","되니","되냐","하냐"
    ]
    # 조사 제거 + 비영숫자 공백화
    clean = re.sub(r"\b([가-힣]{2,10})(은|는|이|가|을|를|에|의|로|으로|도|만|께|에서|까지|보다|부터|한테|에게|하고|와|과)\b", r"\1", text.lower())
    clean = re.sub(r"[^가-힣a-zA-Z0-9]", " ", clean)
    words = [w for w in clean.split() if w not in stopwords and len(w) > 1]

    out = []
    for w in words:
        out.append(w)  # 한글은 원형만 보존
        # ✅ 영문/숫자 토큰만 분해 허용(예: policyNumber → policy, number)
        if re.fullmatch(r"[a-zA-Z0-9]+", w) and len(w) >= 4:
            for i in range(2, len(w)):
                out.append(w[:i])
                out.append(w[i:])
    # 중복 제거(순서 유지)
    return list(dict.fromkeys(out))    # return words

SYNONYM_MAP = {
    "자동차": ["차", "오토", "자차"],
    "자동이체": ["자동 결제", "계좌이체", "이체", "분납자동이체"],
    "카드": ["신용카드", "체크카드"],
    # ✅ 특수 → 일반(방향성만) 추가
    "카드등록": ["카드"],
    "카드변경": ["카드"],
    "배서": ["특약변경", "담보추가", "해지", "권리양도"],
    "인수제한": ["심사", "인수", "심사요청"],
    "구비서류": ["서류", "제출서류"],
}

def expand_synonyms(kwords: list[str]) -> list[str]:
    out = set(kwords)
    for kw in list(kwords):
        for syn in SYNONYM_MAP.get(kw, []):
            # 동의어 문구도 키워드 추출 규칙으로 토큰화해서 추가
            for tok in extract_keywords(syn):
                out.add(tok)
    return list(out)

ACTION_TOKENS = ["등록","변경","해지","취소","결제","정지","해제","추가","삭제","수정"]

def split_compound_korean(term: str):
    # 예: "카드변경" -> ("카드","변경"), "자동이체" -> ("자동이체","")
    for a in ACTION_TOKENS:
        if term.endswith(a) and len(term) > len(a):
            return term[:-len(a)], a
    return term, ""


def add_friendly_prefix(answer):
    answer = answer.strip()
    answer = re.sub(r"^(.*?:)\s*", "", answer)
    if answer.replace(" ", "").startswith("사장님"):
        return answer
    else:
        return f"사장님, {answer} <br> <strong>❤️궁금한거 해결되셨나요?!😊</strong>"

def _parse_attachments(cell_value):
    if not cell_value:
        return []
    if isinstance(cell_value, list):
        data = cell_value
    else:
        try:
            data = json.loads(cell_value)
        except Exception:
            return []
    if isinstance(data, dict):
        data = [data]

    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        mime = item.get("mime", "") or ""
        is_img = item.get("is_image") or mime.startswith("image/")
        out.append({
            "name": item.get("name", ""),
            "mime": mime,
            "view": item.get("view_url") or item.get("embed_url"),
            "embed": item.get("embed_url") or item.get("view_url"),
            "is_image": bool(is_img),
        })
    return out


def _render_attachments_block(cell_value, *, limit=None, show_badge=False) -> str:
    items = _parse_attachments(cell_value)
    if not items:
        return ""

    imgs = [it for it in items if it["is_image"]]
    files = [it for it in items if not it["is_image"]]
    total_imgs = len(imgs)

    if limit is not None:
        imgs = imgs[:max(0, int(limit))]

    # ✅ 이미지 썸네일 (파일명은 캡션으로만 표시)
    img_html = "".join([
        f"""
        <div class="att-image-wrapper">
            <a href="{it['view']}" target="_blank" rel="noreferrer noopener">
                <img class="att-image" src="{it['embed']}" alt="첨부 이미지"/>
            </a>
            <div class="att-caption">{it['name']}</div>
        </div>
        """
        for it in imgs
    ])

    # ✅ 일반 파일은 텍스트 칩 형태
    file_html = "".join([
        f"""<a class="att-chip" href="{it['view']}" target="_blank" rel="noreferrer noopener">📎 {it['name']}</a>"""
        for it in files
    ])

    badge_html = f"""<span class="att-badge">🖼 사진 {total_imgs}</span>""" if (show_badge and total_imgs) else ""

    return f"""
    <div class="att-block">
      {badge_html}
      <div class="att-grid">{img_html}</div>
      <div class="att-files">{file_html}</div>
    </div>
    """

def handle_question(question_input):
    SIMILARITY_THRESHOLD = 0.7
    aesoon_icon = get_character_img_base64(config["image"])
    bot_name = config["bot_name"]
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
    for name_candidate in bot_names:
        if name_candidate in user_txt:
            st.session_state.chat_log.append({
                "role": "user",
                "content": question_input,
                "display_type": "question"
            })
            reply = f"안녕하세요, 사장님! 저는 항상 곁에 있는 {name_candidate}입니다 😊 궁금한 건 뭐든 말씀해 주세요!"
            st.session_state.chat_log.append({
                "role": "bot",
                "content": reply,
                "display_type": "single_answer"
            })
            st.session_state.scroll_to_bottom_flag = True
            return

    # ↓↓↓ Q&A 챗봇 처리 ↓↓↓
    core_kw = normalize_text(question_input)   # 예: "자동 이체" -> "자동이체"
    single_kw_mode = 2 <= len(core_kw) <= 6    # 2~6자면 단일 핵심어 취급

# 2) 단일핵심어일 땐 pending_keyword를 결합하지 않음(세션 영향 차단)
    if st.session_state.pending_keyword and not single_kw_mode:
        user_input = st.session_state.pending_keyword + " " + question_input
        st.session_state.pending_keyword = None
    else:
        user_input = question_input

    try:
        records = get_sheet_records()  # ✅ 캐시 사용(60초)
        indexed, inverted, idf = get_qa_index()  # ✅ 추가: 전처리 인덱스 사용

        q_input_norm = normalize_text(user_input)
        q_input_keywords = extract_keywords(user_input)
        q_input_keywords = expand_synonyms(q_input_keywords)
        core_kw = normalize_text(question_input)
        single_kw_mode = len(core_kw) <= 6 and len(core_kw) >= 2 

        if not q_input_keywords or all(len(k) < 2 for k in q_input_keywords):
           st.session_state.chat_log.append({
               "role": "user",
               "content": question_input,
               "display_type": "question"
           })
           st.session_state.chat_log.append({
                "role": "bot",
                "content": "사장님~ 궁금하신 키워드를 한두 단어라도 입력해 주세요! 예: '카드', '자동이체', '해지' 등 😊",
                "display_type": "single_answer"
           })
           st.session_state.scroll_to_bottom_flag = True
           return


        matched = []
# ✅ [2단계 추가] 이전에 남은 keyword가 있고, 이번에 매칭이 충분하지 않으면 초기화
        if st.session_state.pending_keyword:
            st.session_state.pending_keyword = None

# 1) 키워드로 후보 줄이기 (inverted index)
        candidate_idxs = set()
        for kw in q_input_keywords:
            if single_kw_mode:
                for idx, item in enumerate(indexed):
                    if core_kw and (core_kw in item["q_norm"]):
                        candidate_idxs.add(idx)
            if kw in inverted:
                candidate_idxs.update(inverted[kw])

# 키워드로 후보가 하나도 없으면 전체 탐색 fallback
        if not candidate_idxs:
            candidate_idxs = set(range(len(indexed)))

# 2) 후보만 스코어링 (속도 향상)
        for i in candidate_idxs:
            item = indexed[i]
            r = item["row"]
            sheet_q_norm = item["q_norm"]
            sheet_keywords = item["kwords"]

            match_weight = sum(idf.get(kw, 1.0) for kw in q_input_keywords if kw in sheet_keywords)

            sim_score = 0.0
            if match_weight == 0.0:
                sim_score = get_similarity_score(q_input_norm, sheet_q_norm)

            total_score = match_weight + sim_score

            if len(q_input_keywords) == 1:
                kw0 = q_input_keywords[0]
        # 단일 키워드는 부분일치도 허용
                if any(kw0 in sk or sk in kw0 for sk in sheet_keywords):
                    matched.append((total_score, r))
            else:
        # 복합키워드: 가중치(≥1.8) 또는 유사도(≥0.58) 중 하나만 충족해도 채택
                if match_weight >= 1.8 or sim_score >= 0.58:
                    matched.append((total_score, r))

        matched.sort(key=lambda x: x[0], reverse=True)
        seen_questions = set()
        unique_matched = []
        for score, r in matched:
            if r["질문"] not in seen_questions:
                unique_matched.append((score, r))
                seen_questions.add(r["질문"])
        matched = unique_matched


        if single_kw_mode:
            filtered_matches = matched
        else:
            filtered_matches = [(score, r) for score, r in matched if score >= 1.6]

        if q_input_keywords:
            qnorm = lambda s: normalize_text(s)

            if single_kw_mode:
                # ✅ 합성어 우선: 예) "카드변경" → base="카드", action="변경"
                base, action = split_compound_korean(core_kw)

                if action:
                    # 1순위: base와 action이 모두 포함된 질문
                    strict = [r for score, r in filtered_matches
                              if (base in qnorm(r["질문"])) and (action in qnorm(r["질문"]))]
                    if strict:
                        top_matches = strict[:10]
                    else:
                        # 2순위: 전체 문자열(예: "카드변경") 완전 포함
                        exact = [r for score, r in filtered_matches
                                 if core_kw in qnorm(r["질문"])]
                        if exact:
                            top_matches = exact[:10]
                        else:
                            # 3순위: 일반어(예: "카드")만 포함된 항목
                            fallback = [r for score, r in filtered_matches
                                        if base in qnorm(r["질문"])]
                            top_matches = fallback[:10]
                else:
                    # 일반 단일어(예: "카드")
                    primary = [r for score, r in filtered_matches
                               if (core_kw in qnorm(r["질문"])) or (q_input_norm in qnorm(r["질문"]))]
                    top_matches = primary[:10] if primary else [r for score, r in filtered_matches[:10]]

            else:
                # 복합 키워드: 더 엄격하게 AND
                top_matches = [
                    r for score, r in filtered_matches
                    if (q_input_norm in qnorm(r["질문"])) and any(k in qnorm(r["질문"]) for k in q_input_keywords)
                ]
                if not top_matches:
                    top_matches = [r for score, r in filtered_matches[:10]]

            # 공통 상한
            top_matches = top_matches[:10]

        else:
            top_matches = [r for score, r in filtered_matches[:4]]
        
        st.session_state.chat_log.append({
            "role": "user",
            "content": question_input,
            "display_type": "question"
        })

        # 매칭 5개 이상시 유도질문
        if len(top_matches) >= 5:
            main_word = question_input.strip()
            main_word = re.sub(r"[^가-힣a-zA-Z0-9]", "", main_word)
            COOLDOWN_SECONDS = 6
            now_ts = time.time()
            curr_pending_norm = normalize_text(main_word)
            last_pending_norm = st.session_state.get("last_pending_norm")
            last_pending_at   = st.session_state.get("last_pending_at", 0.0)
            if last_pending_norm == curr_pending_norm and (now_ts - last_pending_at) < COOLDOWN_SECONDS:
                return  # 이번엔 유도질문 카드 생성하지 않음
            # 다음 비교를 위해 최신값 저장
            st.session_state["last_pending_norm"] = curr_pending_norm
            st.session_state["last_pending_at"]   = now_ts

            
            example_pairs = [(m["질문"], add_friendly_prefix(m["답변"])) for m in top_matches[:5]]
            examples_html = "".join([
                f"""
                <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                    <strong style="color:#003399;">질문) {q}</strong><br>
                    <button class="example-ask-btn" data-q="{q.replace('"','&quot;')}"
                      style="margin-top:8px; padding:6px 10px; border-radius:8px; border:1px solid #cbd5e1; cursor:pointer;">
          이 질문으로 다시 물어보기
                    </button>
                    <br>
                    <img src="{aesoon_icon}" width="22" style="vertical-align:middle; margin-right:6px; border-radius:6px;">  {a}
                </div>
                """ for q, a in example_pairs
            ])


            st.session_state.pending_keyword = user_input
            st.session_state.chat_log.append({
    "role": "bot",
    "content": (
        "<div class='example-guide-block'>"
        f"<p><img src='{aesoon_icon}' width='26' style='vertical-align:middle; margin-right:6px; border-radius:6px;'>"
        f"<span class='example-guide-title'>사장님, <b>{main_word}</b>의 어떤 부분이 궁금하신가요?</span>"
        " 유사한 질문이 너무 많아요~ 궁금한 점을 좀 더 구체적으로 입력해 주세요!<br>"
        "<span class='example-guide-emph'><b>아래처럼 다시 물어보시면 바로 답변드릴 수 있어요.</b></span><br>"
        f"{examples_html}"
        "</div>"
        """
        <style>
        .example-guide-block { margin: 10px 0 0 0; font-size: 1.05em; }
        .example-guide-title { color: #226ed8; font-weight: 700; }
        .example-guide-emph  { color: #d32f2f; font-weight: 700; }
        .example-item {
            margin-top: 9px; margin-bottom: 2px; padding-left: 10px;
            line-height: 1.5; border-left: 3px solid #e3e3e3;
            background: #f9fafb; border-radius: 5px; font-size: 0.98em;
        }
        @media (prefers-color-scheme: dark) {
            .example-guide-title { color: #64b5f6; }
            .example-guide-emph  { color: #ffab91; }
            .example-item { background: #232c3a; border-left: 3px solid #374151; color: #eaeaea; }
        }
        </style>
        """
        """
        <script>
        (function(){
          function setInputValueAndSubmit(q){
            const doc = window.parent.document;

            const input = doc.querySelector('textarea, input[type="text"]');
            if (!input) return;

            const proto  = (input.tagName==='TEXTAREA')
                         ? window.parent.HTMLTextAreaElement.prototype
                         : window.parent.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto,'value').set;
            setter.call(input, q);
            input.dispatchEvent(new Event('input', { bubbles:true }));
            input.focus();

            setTimeout(function(){
              const form = input.closest('form');
              if (form && typeof form.requestSubmit === 'function') { form.requestSubmit(); return; }
              if (form) {
                const tmp = doc.createElement('button'); tmp.type='submit'; tmp.style.display='none';
                form.appendChild(tmp); tmp.click(); form.removeChild(tmp); return;
              }
              let btn = doc.querySelector('button[kind="secondaryFormSubmit"]')
                     || doc.querySelector('button[data-testid="baseButton-secondaryFormSubmit"]')
                     || Array.from(doc.querySelectorAll('button')).find(b => /^\s*Enter\s*$/i.test(b.innerText || ''));
              if (btn) { btn.click(); return; }

              input.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
              input.dispatchEvent(new KeyboardEvent('keyup',   {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
            }, 150);
          }

          document.querySelectorAll('.example-ask-btn').forEach(function(btn){
            btn.addEventListener('click', function(){
              const q = this.getAttribute('data-q') || '';
              setInputValueAndSubmit(q);
            });
          });
        })();
        </script>
        """
    ),
    "display_type": "pending"
})

               
            st.session_state.scroll_to_bottom_flag = True
            return


        if len(top_matches) == 1:
            r = top_matches[0]
            bot_answer_content = {
                "q": r["질문"],
                "a": add_friendly_prefix(r["답변"]),
                "files": r.get("첨부_JSON", "")   # ✅ 첨부JSON 전달
                
            }
            bot_display_type = "single_answer"

        elif 2 <= len(top_matches) <= 4:
            bot_answer_content = []
            for r in top_matches:
                bot_answer_content.append({
                    "q": r["질문"],
                    "a": add_friendly_prefix(r["답변"]),
                    "files": r.get("첨부_JSON", "")  # ✅ 첨부JSON 전달
                    
                })
            bot_display_type = "multi_answer"
       

    # 키워드 자체가 부족했던 경우는 이미 위에서 안내했으므로, 이중 응답 막기
            if len(q_input_keywords) == 0 or all(len(k) < 2 for k in q_input_keywords):
                return  # 이미 위에서 안내 멘트 출력됨
            else:
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
    aesoon_icon = get_character_img_base64(config["image"])
    if not aesoon_icon:
        aesoon_icon = get_character_img_base64(BRANCH_CONFIG["default"]["image"])
    bot_name = config["bot_name"]
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
                    files_html = _render_attachments_block(entry["content"].get("files", ""), limit=6, show_badge=False)
                    
                    chat_html_content += (
                        '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                        f"<p style='margin-bottom: 8px;'><strong style='color:#003399;'>질문: {q}</strong></p>"
                        f"<p><img src='{aesoon_icon}' width='26' style='vertical-align:middle; margin-right:6px; border-radius:6px;'> <strong>{bot_name}:</strong><br>{a}</p>"
                        f"{files_html}"
                        '</div></div>'
                    )
                else:
                    bot_answer = str(entry["content"]).replace("\n", "<br>")
                    chat_html_content += (
                        '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                        f"<p><img src='{aesoon_icon}' width='26' style='vertical-align:middle; margin-right:6px; border-radius:6px;'> <strong>{bot_name}:</strong><br>{bot_answer}</p>"
                        '</div></div>'
                    )
            elif entry.get("display_type") == "multi_answer":
                chat_html_content += "<div class='message-row bot-message-row'><div class='message-bubble bot-bubble'>"
                chat_html_content += "<p>🔎 유사한 질문이 여러 개 있습니다:</p>"
                if isinstance(entry["content"], list):
                    for i, pair in enumerate(entry["content"]):
                        q = pair['q'].replace('\n', '<br>')
                        a = pair['a'].replace('\n', '<br>')
                        files_html = _render_attachments_block(pair.get("files", ""), limit=1, show_badge=True)
                        

                        chat_html_content += f"""
                        <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                            <strong style="color:#003399;">{i+1}. 질문: {q}</strong><br>
                            <img src='{aesoon_icon}' width='22' style='vertical-align:middle; margin-right:6px; border-radius:6px;'> <strong>{bot_name}:</strong> {a}
                             {files_html}
                             
                        </div>
                        """
                elif isinstance(entry["content"], dict):
                    q = entry["content"].get('q', '').replace('\n', '<br>')
                    a = entry["content"].get('a', '').replace('\n', '<br>')
                    chat_html_content += f"""
                        <div class='chat-multi-item' style="margin-bottom: 22px; padding: 14px 18px; border-radius: 14px; border: 1.5px solid #e3e3e3; background: #fcfcfd;">
                            <strong style="color:#003399;">질문: {q}</strong><br>
                            <img src='{aesoon_icon}' width='22' style='vertical-align:middle; margin-right:6px; border-radius:6px;'> <strong>{bot_name}:</strong> {a}
                        </div>
                        """
                chat_html_content += "</div></div>"
            elif entry.get("display_type") == "pending":
                chat_html_content += (
                    '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                    f"<style='color:#ff914d;font-weight:600;'>{entry['content']}"
                    '</div></div>'
                )
            elif entry.get("display_type") == "llm_answer":
                bot_answer = str(entry["content"]).replace("\n", "<br>")
                chat_html_content += (
                    '<div class="message-row bot-message-row"><div class="message-bubble bot-bubble">'
                    f"<p><img src='{aesoon_icon}' width='26' style='vertical-align:middle; margin-right:6px; border-radius:6px;'> <strong>{bot_name}:</strong><br>{bot_answer}</p>"
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
<style id="attachments-style">
  .att-block{ margin-top:10px; position:relative; }
  .att-grid{ display:flex; flex-wrap:wrap; gap:8px; }
  .att-thumb{ display:block; width:120px; height:90px; overflow:hidden; border-radius:8px; border:1px solid #e5e7eb; background:#fff; }
  .att-thumb img{ width:100%; height:100%; object-fit:cover; display:block; }
  .att-files{ margin-top:8px; display:flex; gap:8px; flex-wrap:wrap; }
  .att-chip{ display:inline-block; padding:6px 10px; border:1px solid #e5e7eb; border-radius:8px; background:#f8fafc; text-decoration:none; }

  .att-badge{
    position:absolute; top:-8px; right:-4px; 
    background:#111; color:#fff; font-size:12px; line-height:1;
    padding:4px 8px; border-radius:999px; box-shadow:0 2px 8px rgba(0,0,0,.15);
  }

.att-image-wrapper {
  display: inline-block;
  margin: 6px;
  text-align: center;
}

.att-image {
  max-width: 220px;
  max-height: 160px;
  border-radius: 10px;
  border: 1px solid #ddd;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.2s;
}

.att-image:hover {
  transform: scale(1.05);
}

.att-caption {
  margin-top: 4px;
  font-size: 0.8em;
  color: #555;
  word-break: break-all;
}

  @media(prefers-color-scheme:dark){
    .att-thumb{ border-color:#374151; background:#111; }
    .att-chip{ border-color:#374151; background:#222; color:#e5e7eb; }
    .att-badge{ background:#444; color:#fff; }
  }
</style>
<style id="layout-fix">
  /* 인사말(인트로)만 전체폭 사용 */
  #chat-content-scroll-area { 
     width:100% !important; 
     max-width:100% !important;
     padding-bottom: calc(env(safe-area-inset-bottom, 0px) + 96px);
  }

  .intro-message-row { width:100% !important; display:block !important; }
  .intro-bubble { width:100% !important; max-width:100% !important; display:block !important; box-sizing:border-box; }
  /* 혹시 다른 곳에서 max-width를 제한하면 무시 */
  .message-bubble.intro-bubble { max-width:100% !important; }
  .intro-bubble * { overflow-wrap: anywhere; word-break: keep-all; }
</style>

<style id="dynamic-color-style">
/* 기본(라이트) */
.message-row, .message-bubble, .bot-bubble, .intro-bubble,
.message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p {
  color: #111 !important;
}
.user-bubble, .user-bubble p {
  color: #111 !important;
}
</style>
<script>
function applyLight() {
  var styleTag = document.getElementById('dynamic-color-style');
  styleTag.innerHTML = `
.message-row, .message-bubble, .bot-bubble, .intro-bubble,
.message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p { color:#111 !important; }
.user-bubble, .user-bubble p { color:#111 !important; }
.message-bubble a, .bot-bubble a { color: #0645ad !important; text-decoration: underline; }
.intro-bubble li, .bot-bubble li { color: #111 !important; }
`;
}
function applyDark() {
  var styleTag = document.getElementById('dynamic-color-style');
  styleTag.innerHTML = `
.message-row, .message-bubble, .bot-bubble, .intro-bubble,
.message-bubble p, .message-bubble strong, .bot-bubble p, .intro-bubble h2, .intro-bubble p { color:#eeeeee !important; }
/* 사용자 말풍선은 배경/글자색을 강제로 바꿔 가독성 확보 (inline 스타일 덮기 위해 !important) */
.user-bubble { background:#2a2a2a !important; }
.user-bubble, .user-bubble p { color:#eeeeee !important; }
.message-bubble a, .bot-bubble a { color: #8ab4f8 !important; text-decoration: underline; }
.intro-bubble li, .bot-bubble li { color: #eeeeee !important; }
`;
}
function updateColorMode() {
  let isDark = false;
  try {
    isDark = window.parent.matchMedia && window.parent.matchMedia('(prefers-color-scheme: dark)').matches;
  } catch(e) {}
  if (isDark) applyDark(); else applyLight();
}
updateColorMode();
if (window.parent.matchMedia) {
  window.parent.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateColorMode);
}
</script>
"""
    return f"""
    {chat_style}
    <div id="chat-content-scroll-area" style="width:100%; max-width:100%;">
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

 # 2. 음성 + 새로고침(같은 줄)
st.markdown('<div id="toolbar-anchor"></div>', unsafe_allow_html=True)
components.html("""
<style>
#toolbar-row{
  display:flex; align-items:center; justify-content:space-between;
  gap:12px; width:100%; margin:4px 0 6px; flex-wrap:nowrap; min-width:0;
}
#voice-block{ display:flex; align-items:center; gap:10px; min-width:0; flex:1 1 auto; }
#toggleRecord{
  background:#238636; color:#fff; font-weight:bold; border:none; border-radius:8px;
  font-size:15px; padding:6px 16px; height:36px; min-width:80px; box-shadow:0 2px 8px rgba(0,64,0,0.10);
  cursor:pointer; transition:all .3s ease;
}
#toggleRecord:hover{ background:#008000; color:#ffeb3b; }
#speech_status{ font-size:.85em; color:#1b5e20; margin-left:4px; display:none; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#hardRefreshBtn{
  flex:0 0 auto; height:36px; padding:6px 12px; border-radius:8px; border:1px solid #e5e7eb;
  background:#f6f8fa; font-weight:700; cursor:pointer; white-space:nowrap;
}
#hardRefreshBtn:hover{ background:#eef2f6; }
@media (max-width:420px){
  #toggleRecord, #hardRefreshBtn{ font-size:14px; padding:6px 10px; }
}
@media (prefers-color-scheme: dark){
  #hardRefreshBtn{ border-color:#374151; background:#2a2f36; color:#e5e7eb; }
  #hardRefreshBtn:hover{ background:#3a4049; }
}
</style>

<div id="toolbar-row">
  <div id="voice-block">
    <button id="toggleRecord">🎤 음성</button>
    <div id="speech_status"></div>
  </div>
  <button id="hardRefreshBtn" title="처음 화면으로">🔁 새로고침</button>
</div>

<script>
let isRecording = false;
let recognition;

function doHardRefresh(){
  const doc = window.parent.document;
  const url = new URL(doc.location.href);
  url.searchParams.set('hardreset','1');
  url.searchParams.set('ts', Date.now().toString());
  doc.location.replace(url.toString());
}
document.getElementById("hardRefreshBtn").addEventListener("click", doHardRefresh);

document.getElementById("toggleRecord").addEventListener("click", function () {
  const input  = window.parent.document.querySelector('textarea, input[type=text]');
  const status = document.getElementById("speech_status");
  if (input) input.focus();

  if (!isRecording) {
    recognition = new webkitSpeechRecognition();
    recognition.lang = "ko-KR";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = function (event) {
      let fullTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        fullTranscript += event.results[i][0].transcript;
      }
      const proto  = (input && input.tagName === 'TEXTAREA')
                   ? window.HTMLTextAreaElement.prototype
                   : window.HTMLInputElement.prototype;
      const setter = Object.getOwnPropertyDescriptor(proto, "value").set;
      setter.call(input, fullTranscript);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      status.style.display = "inline";
      status.innerText = "🎤 음성 입력 중!";
    };

    recognition.onerror = function (e) {
      status.style.display = "inline";
      status.innerText = "⚠️ 오류: " + e.error;
      isRecording = false;
      document.getElementById("toggleRecord").innerText = "🎤 음성";
    };

    recognition.onend = function () {
      isRecording = false;
      document.getElementById("toggleRecord").innerText = "🎤 음성";
      status.style.display = "inline";
      status.innerText = "🛑 음성 인식 종료되었습니다.";

      setTimeout(function () {
        const doc   = window.parent.document;
        const input = doc.querySelector('textarea, input[type="text"]');
        if (input) {
          const form = input.closest('form');
          if (form && typeof form.requestSubmit === 'function') { form.requestSubmit(); return; }
          else if (form) {
            const tmp = doc.createElement('button'); tmp.type='submit'; tmp.style.display='none';
            form.appendChild(tmp); tmp.click(); form.removeChild(tmp); return;
          }
        }
        let btn = doc.querySelector('button[kind="secondaryFormSubmit"]')
                 || doc.querySelector('button[data-testid="baseButton-secondaryFormSubmit"]');
        if (!btn) {
          const buttons = Array.from(doc.querySelectorAll('button'));
          btn = buttons.find(b => b.innerText && b.innerText.trim() === "Enter");
        }
        if (btn) { btn.click(); return; }
        if (input) {
          input.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true}));
        }
      }, 800);
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
""", height=60)

st.markdown('<div class="input-form-fixed">', unsafe_allow_html=True)

with st.form("input_form", clear_on_submit=True):
    question_input = st.text_input("궁금한 내용을 입력해 주세요", key="input_box")
    submitted = st.form_submit_button("Enter")
    if submitted and question_input:
        # 1) 6초 내 동일 내용 재제출(오타 없는 순수 중복) 차단
        now_ts = time.time()
        curr_norm = normalize_text(question_input)
        last_norm = st.session_state.get("last_input_norm")
        last_at   = st.session_state.get("last_input_at", 0.0)

        if last_norm == curr_norm and (now_ts - last_at) < DEDUPE_WINDOW_SEC:
            st.stop()  # 이후 코드(로그/처리) 중단

        st.session_state["last_input_norm"] = curr_norm
        st.session_state["last_input_at"] = now_ts

        # 2) 시그니처 기반(지점+질문) 중복 차단
        _branch = get_branch_param()
        if is_duplicate_submit(question_input, _branch):
            st.stop()

        # 3) 로그 기록 후 처리
        kst = pytz.timezone("Asia/Seoul")
        now = datetime.now(kst)
        append_log_row_to_logs([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            _branch,
            question_input.strip()
        ])
        handle_question(question_input)
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

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

@media (min-width: 1100px) {
    .input-form-fixed,
    .input-form-fixed form,
    .input-form-fixed [data-testid="stTextInputRootElement"],
    .input-form-fixed [data-testid="stTextAreaRootElement"] {
        max-width: 900px;
        margin: 0 auto;
        width: 100%;
        border-radius: 8px;
    }
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