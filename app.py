import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import base64
import difflib
import re
import json

# ===== 1. 세션 초기화 =====
if "chat_log" not in st.session_state:
    st.session_state.chat_log = [
        {"role": "intro", "content": "안녕하세요! 충청호남본부 도우미 애순이에요.❤️ 궁금하신 점을 아래에 입력해 주세요!"}
    ]

# ===== 2. 구글시트 연동 =====
try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # secrets.toml 또는 환경변수에서 서비스 계정 json 정보 불러오기
    # 반드시 'gcp_service_account' 항목에 본부장님 json 문자열이 있어야 함
    json_key_dict = json.loads(st.secrets["gcp_service_account"])
    credentials = Credentials.from_service_account_info(json_key_dict, scopes=scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
    records = sheet.get_all_records()
except Exception as e:
    records = []
    st.error(f"❌ 구글시트 연결 오류: {e}")

# ===== 3. 텍스트 정규화/유사도 =====
def normalize(text):
    return re.sub(r"[^가-힣a-zA-Z0-9]", "", str(text).lower().strip())

def similarity(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

# ===== 4. Q&A 답변 매칭 =====
def find_answer(user_q):
    norm_q = normalize(user_q)
    if not norm_q: return None, None
    matches = []
    for row in records:
        sheet_q = normalize(row.get("질문",""))
        score = similarity(norm_q, sheet_q)
        if norm_q in sheet_q or sheet_q in norm_q or score > 0.65:
            matches.append((score, row))
    matches.sort(reverse=True)
    if len(matches) == 0:
        return None, None
    elif len(matches) == 1:
        return matches[0][1]["질문"], matches[0][1]["답변"]
    else:
        # 여러개 유사하면 5개까지 예시, 가장 유사한 답변 1개
        example_qs = [m[1]["질문"] for m in matches[:5]]
        main_q, main_a = matches[0][1]["질문"], matches[0][1]["답변"]
        return example_qs, main_a

# ===== 5. 챗UI 전체 렌더 =====
def render_chat():
    html = ""
    for m in st.session_state.chat_log:
        if m["role"]=="intro":
            html += f"""
                <div style='display:flex;align-items:flex-start;margin-bottom:18px;'>
                  <img src='https://files.oaiusercontent.com/file-MBd11aLKgJMPkclR2Wi5RbKY?se=2024-07-19T07%3A13%3A07Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image&skoid=9e0d1fdf-4d59-4322-80e2-e1051340401e&sktid=41c0e59c-bd5d-4d36-90ec-e19f19ba3af3&skt=2024-07-20T01%3A27%3A07Z&ske=2024-07-21T01%3A27%3A07Z&sks=b&skv=2021-08-06&sig=RKkdlgnPlwRKZkSvl5mE8PtzA1T5k6wYnw9Rk%2BOd9ZY%3D'
                       width='90' style='margin-right:17px; border-radius:16px; border:1px solid #eee;'>
                  <div>
                      <h2 style='margin:0 0 8px 0;font-weight:700;'>사장님, 안녕하세요!!</h2>
                      <p>충청호남본부 도우미 ‘애순이’에요.❤️<br>
                      궁금하신 거 있으시면 언제든 물어봐 주세요!</p>
                      <p><b style="color:#D32F2F;">유지율도 조금만 더 챙겨주세요^*^😊</b></p>
                      <p><b style="color:#003399;">사장님!! 오늘도 화이팅!!!</b></p>
                  </div>
                </div>
            """
        elif m["role"]=="user":
            html += f"<div style='text-align:right;margin:8px 0;'><b style='color:#111;'>{m['content']}</b></div>"
        elif m["role"]=="bot":
            html += f"<div style='text-align:left;color:#226ed8;margin:8px 0;'><b>애순이:</b> {m['content']}</div>"
    html += "<div id='bottom'></div>"
    st.markdown(html, unsafe_allow_html=True)
    # 채팅창 자동 스크롤
    st.markdown("""
    <script>
    window.scrollTo(0,document.body.scrollHeight);
    document.getElementById('bottom').scrollIntoView({behavior:"auto", block:"end"});
    </script>
    """, unsafe_allow_html=True)

# ===== 6. 질문 입력폼 (하단 고정, 엔터/버튼/음성) =====
st.markdown("""
    <style>
    .fixed-bottom { position:fixed;left:0;right:0;bottom:0;z-index:9999;background:#fff;box-shadow:0 -2px 16px rgba(0,0,0,0.08);}
    .fixed-row { display:flex;align-items:center;gap:6px;padding:15px 8px;}
    .mic-btn {background:#238636;color:#fff;padding:0.7em 1em;border:none;border-radius:10px;font-size:19px;}
    .ask-btn {background:#238636;color:#fff;padding:0.7em 1.2em;border:none;border-radius:10px;font-weight:bold;font-size:18px;}
    .input-box {flex:1;font-size:18px;padding:11px 16px;border-radius:10px;border:1px solid #bbb;}
    </style>
    <div class='fixed-bottom'>
      <div class='fixed-row'>
        <button id='micBtn' class='mic-btn'>🎤</button>
        <input id='chatInput' class='input-box' type='text' placeholder='궁금한 내용을 입력해 주세요' autocomplete='off'/>
        <button id='askBtn' class='ask-btn'>질문</button>
      </div>
      <div id='speech_status' style='color:gray;font-size:0.9em;margin-top:3px;'></div>
    </div>
    <script>
    // 엔터키 입력
    document.getElementById('chatInput').addEventListener('keydown', function(e){
        if(e.key==='Enter'){
            document.getElementById('askBtn').click();
        }
    });
    // 질문 버튼 클릭
    document.getElementById('askBtn').onclick = function(){
        var v = document.getElementById('chatInput').value.trim();
        if(v.length > 0){
            window.parent.postMessage({chat_input:v},"*");
            document.getElementById('chatInput').value='';
        }
    };
    // 음성인식(Chrome에서만 정상)
    document.getElementById("micBtn").onclick = function(){
        var status = document.getElementById("speech_status");
        var input = document.getElementById("chatInput");
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
            setTimeout(()=>{ status.innerText=""; }, 1200);
        };
        recog.onerror = function(e){
            status.innerText = "⚠️ 오류: " + e.error;
            setTimeout(()=>{ status.innerText=""; }, 1200);
        };
        recog.onend = function(){ status.innerText = ""; }
        recog.start();
        status.innerText = "🎤 음성 인식 중입니다...";
    };
    </script>
""", unsafe_allow_html=True)

# ===== 7. JS → Streamlit로 질문 전달 (postMessage) =====
input_value = st.query_params.get("chat_input")
if input_value:
    user_q = input_value.strip()
    st.session_state.chat_log.append({"role":"user", "content":user_q})
    q_matched, a = find_answer(user_q)
    if a is None:
        reply = "사장님, 죄송해요. 아직 준비가 안된 질문입니다. 매니저에게 말씀해 주세요."
    elif isinstance(q_matched, list):  # 유사질문 예시가 여러개면
        reply = (
            f"<b>유사 질문이 여러 개 있어요!</b><br>"
            + "<br>".join([f"예시) <span style='color:#226ed8;'>{qq}</span>" for qq in q_matched])
            + f"<br><br><b>가장 가까운 답변:</b><br>{a}"
        )
    else:
        reply = a
    st.session_state.chat_log.append({"role": "bot", "content": reply})
    # 입력값 쿼리스트링 삭제(중복방지)
    st.experimental_set_query_params()
    st.experimental_rerun()

# ===== 8. 채팅창 전체 렌더 =====
render_chat()
