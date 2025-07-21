import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import base64
import difflib
import re
import json
import os

# === [1] 애순이 캐릭터 이미지 ===
def get_character_img():
    img_path = "aesoon_character.png"   # 같은 폴더에 png 저장 권장
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    # Fallback: 외부 이미지 URL
    return "https://static.thenounproject.com/png/3636392-200.png"  # 임시(여자 매니저 스타일)

# === [2] 구글시트 연결 ===
@st.cache_resource(show_spinner=False)
def get_qa():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        json_key_dict = json.loads(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
        return sheet.get_all_records()
    except Exception as e:
        st.error(f"❌ 구글시트 오류: {e}")
        return []

qa_list = get_qa()

# === [3] 챗 세션 ===
if "chat" not in st.session_state:
    st.session_state.chat = [
        {"role":"intro", "msg":"사장님, 안녕하세요! 충청호남본부 도우미 애순이에요.❤️ 궁금하신 점을 아래에 입력해 주세요!"}
    ]

# === [4] Q&A 매칭 ===
def clean(t): return re.sub(r"[^가-힣a-zA-Z0-9]", "", str(t).lower())
def find_answer(q):
    normq = clean(q)
    results = []
    for row in qa_list:
        sheet_q = clean(row.get("질문",""))
        if not sheet_q: continue
        score = difflib.SequenceMatcher(None, normq, sheet_q).ratio()
        if normq in sheet_q or sheet_q in normq or score > 0.68:
            results.append((score, row))
    results.sort(reverse=True)
    if len(results)==0:
        return None
    elif len(results)==1:
        return results[0][1]["답변"]
    else:
        # 유사 질문 여러 개일 때
        example = " / ".join([r[1]["질문"] for r in results[:4]])
        return f"유사 질문이 많아요! 예시: {example}\n\n대표 답변: {results[0][1]['답변']}"

# === [5] 채팅창 출력 ===
def chat_ui():
    st.markdown("""
    <style>
    .chat-row {margin:10px 0;}
    .chat-intro {display:flex;align-items:flex-start;}
    .chat-img {width:70px;height:70px;border-radius:16px;border:1.5px solid #eee;margin-right:18px;}
    .chat-bot {background:#f2f5ff;border-radius:12px;padding:16px 18px 16px 18px;max-width:550px;}
    .chat-user {background:#c5ffdc;border-radius:12px;padding:14px 22px;margin-left:auto;max-width:70%;}
    </style>
    """, unsafe_allow_html=True)
    for m in st.session_state.chat:
        if m["role"] == "intro":
            st.markdown(f"""
            <div class="chat-row chat-intro">
              <img src="{get_character_img()}" class="chat-img"/>
              <div class="chat-bot">
                <b style="font-size:2.2rem;">사장님, 안녕하세요!!</b><br>
                <span style="font-size:1.2rem;">충청호남본부 도우미 '애순이'에요.❤️</span><br><br>
                궁금하신 거 있으시면 언제든 물어봐 주세요!<br>
                <b style="color:#d32f2f;">유지율도 조금만 더 챙겨주세요^*^😊</b><br>
                <b style="color:#003399;">사장님!! 오늘도 화이팅!!!</b>
              </div>
            </div>
            """, unsafe_allow_html=True)
        elif m["role"] == "user":
            st.markdown(f'<div class="chat-row chat-user">{m["msg"]}</div>', unsafe_allow_html=True)
        elif m["role"] == "bot":
            st.markdown(f'<div class="chat-row chat-bot">{m["msg"]}</div>', unsafe_allow_html=True)

    st.markdown('<div id="chat-bottom"></div>', unsafe_allow_html=True)
    st.markdown("""
    <script>setTimeout(function(){document.getElementById("chat-bottom").scrollIntoView({behavior:"smooth",block:"end"});},100);</script>
    """, unsafe_allow_html=True)

chat_ui()

# === [6] 하단 입력창 (st.form 활용) ===
with st.form("chat_form", clear_on_submit=True):
    cols = st.columns([1,7,1])
    with cols[0]:
        st.markdown(
            '<button id="micBtn" style="width:54px;height:54px;font-size:2rem;background:#238636;color:#fff;border:none;border-radius:12px;">🎤</button>',
            unsafe_allow_html=True
        )
    with cols[1]:
        q = st.text_input("", key="chat_input", label_visibility="collapsed", placeholder="궁금한 내용을 입력해 주세요")
    with cols[2]:
        submitted = st.form_submit_button("질문", use_container_width=True)

# === [7] 입력/음성연동 처리 ===
# (음성인식: 버튼 누르면 브라우저 음성 → 입력창에 텍스트 자동 입력, submit 버튼은 누르지 않음)
st.markdown("""
<script>
document.getElementById('micBtn').onclick = function(e){
    e.preventDefault();
    var input = window.parent.document.querySelector('input[id^="chat_input"]');
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition){
        alert("음성 인식이 지원되지 않습니다 (크롬 PC/모바일 권장)");
        return false;
    }
    var recog = new (window.SpeechRecognition||window.webkitSpeechRecognition)();
    recog.lang = "ko-KR";
    recog.onresult = function(ev){
        input.value = ev.results[0][0].transcript;
        input.dispatchEvent(new Event('input', { bubbles: true }));
    };
    recog.start();
    return false;
};
</script>
""", unsafe_allow_html=True)

# === [8] 실제 질문 처리 ===
if submitted and q.strip():
    st.session_state.chat.append({"role":"user", "msg":q.strip()})
    answer = find_answer(q.strip())
    if answer:
        st.session_state.chat.append({"role":"bot", "msg":answer})
    else:
        st.session_state.chat.append({"role":"bot", "msg":"아직 준비되지 않은 질문이에요! 매니저에게 문의해 주세요."})
    st.experimental_rerun()  # 자동 스크롤 및 리렌더

