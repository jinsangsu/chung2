import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import difflib
import re
import base64
import os
import json

# ======= 스타일 =======
st.markdown("""
<style>
.stApp { padding-bottom: 120px !important; }
.input-form-fixed { position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#fff;
  box-shadow:0 -2px 16px rgba(0,0,0,0.07);padding:12px 8px 12px 8px;}
@media (max-width: 600px) { .input-form-fixed { padding-bottom: 16px !important; } }
</style>
""", unsafe_allow_html=True)

# ======= 캐릭터/인사말 =======
def get_intro_html():
    img_path = "managerbot_character.webp"
    if os.path.exists(img_path):
        with open(img_path, "rb") as img_file:
            b64 = base64.b64encode(img_file.read()).decode("utf-8")
            img_tag = f'<img src="data:image/webp;base64,{b64}" width="75" style="margin-right:17px; border-radius:16px; border:1px solid #eee;">'
    else:
        img_tag = ''
    return f"""
    <div style="display: flex; align-items: flex-start; margin-bottom:18px;">
        {img_tag}
        <div>
            <h2 style='margin:0 0 8px 0;font-weight:700;'>사장님, 안녕하세요!!</h2>
            <p>충청호남본부 도우미 ‘애순이’에요.❤️</p>
            <p>궁금하신거 있으시면<br>여기서 먼저 물어봐 주세요!<br>궁금하신 내용을 입력하시면 되여~</p>
            <p>예를들면 자동차, 카드등록, 자동이체 등...<br>제가 아는 건 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>늘 옆에서 제가 함께하겠습니다.</p>
            <p><strong style="font-weight:900; color:#D32F2F;">유지율도 조금만 더 챙겨주세요^*^😊</strong></p>
            <strong style="font-weight:900; color:#003399;">사장님!! 오늘도 화이팅!!!</strong>
        </div>
    </div>
    """

# ======= 구글시트 연결 =======
SHEET_ID = "1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo"
SHEET_NAME = "질의응답시트"
sheet = None
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    json_key_dict = json.loads(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
except Exception as e:
    st.error(f"❌ 구글 시트 연동에 실패했습니다: {e}")

# ======= 세션 초기화 =======
if "chat_log" not in st.session_state:
    st.session_state.chat_log = [{"role": "intro", "content": "", "display_type": "intro"}]
if "pending_keyword" not in st.session_state:
    st.session_state.pending_keyword = None

# ======= 챗봇 답변 =======
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
    SIMILARITY_THRESHOLD = 0.5
    user_txt = question_input.strip().replace(" ", "").lower()
    chit_chat_patterns = [
        (["사랑", "좋아해"], "사장님, 저도 사랑합니다! 💛 언제나 사장님 곁에 있을게요!"),
        (["잘지내", "안녕"], "네! 사장님 덕분에 잘 지내고 있습니다😊 사장님은 잘 지내셨어요?"),
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
                "role": "user", "content": question_input, "display_type": "question"
            })
            st.session_state.chat_log.append({
                "role": "bot", "content": reply, "display_type": "single_answer"
            })
            return
    if "애순" in user_txt:
        st.session_state.chat_log.append({
            "role": "user", "content": question_input, "display_type": "question"
        })
        reply = "사장님! 애순이 항상 곁에 있어요 😊 궁금한 건 뭐든 말씀해 주세요!"
        st.session_state.chat_log.append({
            "role": "bot", "content": reply, "display_type": "single_answer"
        })
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
            "role": "user", "content": question_input, "display_type": "question"
        })
        if len(matched) >= 5:
            main_word = question_input.strip()
            main_word = re.sub(r"[^가-힣a-zA-Z0-9]", "", main_word)
            example_questions = [m["질문"] for m in matched[:5]]
            examples_html = "".join([
                f"<div class='example-item'>예시) {q}</div>"
                for q in example_questions
            ])
            st.session_state.pending_keyword = user_input
            st.session_state.chat_log.append({
                "role": "bot", "content": (
                    "<div class='example-guide-block'>"
                    f"<span class='example-guide-title'>사장님, <b>{main_word}</b>의 어떤 부분이 궁금하신가요?</span>"
                    " 유사한 질문이 너무 많아요~ 궁금한 점을 좀 더 구체적으로 입력해 주세요!<br>"
                    "<span class='example-guide-emph'><b>아래처럼 다시 물어보시면 바로 답변드릴 수 있어요.</b></span><br>"
                    f"{examples_html}"
                    "</div>"), "display_type": "pending"
            })
            return
        if len(matched) == 1:
            bot_answer_content = {
                "q": matched[0]["질문"], "a": add_friendly_prefix(matched[0]["답변"])
            }
            bot_display_type = "single_answer"
        elif len(matched) > 1:
            bot_answer_content = []
            for r in matched:
                bot_answer_content.append({
                    "q": r["질문"], "a": add_friendly_prefix(r["답변"])
                })
            bot_display_type = "multi_answer"
        else:
            st.session_state.chat_log.append({
                "role": "bot", "content": "사장님~~죄송해요.. 아직 준비가 안된 질문이에요. 급하시면 저한테 와주세요~",
                "display_type": "single_answer"
            })
            return
        if len(matched) > 0:
            st.session_state.chat_log.append({
                "role": "bot", "content": bot_answer_content, "display_type": bot_display_type
            })
    except Exception as e:
        st.session_state.chat_log.append({
            "role": "bot", "content": f"❌ 오류 발생: {e}", "display_type": "llm_answer"
        })

# ======= 챗UI =======
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
                for i, pair in enumerate(entry["content"]):
                    q = pair['q'].replace('\n', '<br>')
                    a = pair['a'].replace('\n', '<br>')
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
    }, 100);
    </script>
    """
    return f"""
    <div id="chat-content-scroll-area" style="padding-bottom:120px;">
        {chat_html_content}
        <div id="chat-scroll-anchor"></div>
    </div>
    {scroll_iframe_script}
    """

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.components.v1.html(display_chat_html_content(), height=520, scrolling=True)

# ======= 하단 입력 + 음성버튼 (HTML/JS) =======
import streamlit.components.v1 as components

components.html("""
<div class="input-form-fixed">
    <form id="custom-chat-form" style="display:flex;gap:8px;">
        <button id="micBtn" type="button" style="background:#238636;color:#fff;border-radius:10px;border:none;font-weight:bold;font-size:16px;padding:10px 14px;cursor:pointer;">🎤</button>
        <input id="custom-chat-input" type="text" placeholder="궁금한 내용을 입력해 주세요" style="flex:1;font-size:17px;padding:10px 16px;border-radius:10px;border:1px solid #ddd;" autocomplete="off" />
        <button type="submit" style="background:#238636;color:#fff;border-radius:10px;border:none;font-weight:bold;font-size:16px;padding:10px 20px;cursor:pointer;">질문</button>
    </form>
    <div id="speech_status" style="color:#777;font-size:0.95em;margin-top:3px;"></div>
</div>
<script>
var input = document.getElementById("custom-chat-input");
document.getElementById("custom-chat-form").onsubmit = function(e){
    e.preventDefault();
    var v = input.value.trim();
    if (v.length > 0) {
        window.parent.postMessage({chat_input: v}, "*");
        input.value = "";
    }
    setTimeout(function(){
        input.focus();
        input.scrollIntoView({behavior:"smooth", block:"end"});
    }, 150);
    return false;
};
input.addEventListener("keydown", function(e){
    if(e.key==="Enter"){ document.getElementById("custom-chat-form").dispatchEvent(new Event("submit")); }
});
document.getElementById("micBtn").onclick = function(){
    var status = document.getElementById("speech_status");
    var input = document.getElementById("custom-chat-input");
    if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
        status.innerText = "음성 인식이 지원되지 않습니다.";
        return;
    }
    var recog = new (window.SpeechRecognition||window.webkitSpeechRecognition)();
    recog.lang = "ko-KR";
    recog.interimResults = false;
    recog.onresult = function(event){
        var txt = "";
        for (var i = event.resultIndex; i < event.results.length; i++) {
            txt += event.results[i][0].transcript;
        }
        input.value = txt;
        status.innerText = "🎤 인식됨: " + txt;
        setTimeout(()=>{ status.innerText=""; }, 2000);
    };
    recog.onerror = function(e){
        status.innerText = "⚠️ 오류: " + e.error;
        setTimeout(()=>{ status.innerText=""; }, 2000);
    };
    recog.start();
    status.innerText = "🎤 음성 인식 중입니다...";
};
</script>
""", height=100)

# ======= Streamlit 질문 입력 감지 & 처리 =======
custom_input = st.query_params.get('streamlit_set_input', [None])[0]
if "last_custom_input" not in st.session_state:
    st.session_state.last_custom_input = None
if custom_input and custom_input != st.session_state.last_custom_input:
    handle_question(custom_input)
    st.session_state.last_custom_input = custom_input
    st.experimental_rerun()
