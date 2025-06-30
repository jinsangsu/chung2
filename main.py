
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai # 새로 추가
import os # os는 API 키 환경 변수 로드를 위해 유지합니다.

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import gspread
from google.oauth2.service_account import Credentials
import difflib
from sentence_transformers import SentenceTransformer, util
import torch
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')  # 모델 캐싱


def get_semantic_similarity(q1, q2):
    emb1 = model.encode(q1, convert_to_tensor=True)
    emb2 = model.encode(q2, convert_to_tensor=True)
    return float(util.pytorch_cos_sim(emb1, emb2))

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 구글 시트 연결
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    creds = Credentials.from_service_account_file("aesoonkey.json", scopes=scope)
    client = gspread.authorize(creds)
    worksheet = client.open_by_key("1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    print("❌ Google Sheet 연결 실패:", e)
    worksheet = None

class ChatRequest(BaseModel):
    message: str

def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()

SIMILARITY_THRESHOLD = 0.4

@app.post("/chat")
async def chat(request: ChatRequest):
    if worksheet is None:
        return JSONResponse(content={"reply": "시트를 불러올 수 없습니다. 관리자에게 문의해주세요."})

    message_raw = request.message.strip().lower()
        
    message_no_space = message_raw.replace(" ", "")

    records = worksheet.get_all_records()
    best_match = None
    best_score = 0.0
    threshold = 0.4

    for r in records:
        q = r["질문"].strip().lower()
        q_no_space = q.replace(" ", "")

        score1 = get_semantic_similarity(message_raw, q)
        score2 = get_semantic_similarity(message_no_space, q_no_space)
        score3 = get_similarity_score(message_raw, q)
        

        final_score = max(score1, score2, score3)

        if final_score > threshold and final_score > best_score:
            best_match = r
            best_score = final_score

   if best_match:
    return {"reply": best_match["답변"]}
else:
    try:
        # Gemini 모델 초기화
        # 'gemini-pro'는 텍스트 기반 일반 모델입니다.
        # 이미지/텍스트 혼합 모델은 'gemini-pro-vision'을 사용할 수 있습니다.
        model = genai.GenerativeModel('gemini-pro')

        # Gemini에 보낼 시스템 프롬프트와 사용자 메시지를 결합합니다.
        # Gemini는 아직 별도의 'system' 역할을 명시적으로 지원하지 않으므로,
        # 'system' 메시지를 사용자 메시지 앞에 넣어 주는 것이 일반적인 방법입니다.
        full_prompt = (
            "당신은 KB손해보험 개인영업 설계사들을 도와주는 친절하고 유쾌한 여성 매니저 애순이입니다. "
            "사용자가 인삿말(예: '애순아', '안녕', '하이') 또는 일상적인 말을 하면 반드시 상냥하게 대답해 주세요. "
            "절대로 무응답하지 마세요. 보험 관련 질문이 아니어도 반드시 성의 있게 대답해 주세요.\n\n"
            f"사용자 질문: {request.message}"
        )

        # Gemini 모델 호출
        # 'temperature'는 모델의 창의성/다양성을 조절합니다. 0.7은 OpenAI와 유사한 수준입니다.
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )

        # Gemini 응답 추출
        # 응답이 비어있을 경우를 대비한 처리도 포함합니다.
        if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            # parts[0].text로 응답 텍스트를 가져옵니다.
            gemini_reply = response.candidates[0].content.parts[0].text.strip()
            if not gemini_reply:
                gemini_reply = "사장님, 어떤 도움이 필요하신가요? 😊"
        else:
            gemini_reply = "애순이가 잠시 자리를 비운 것 같아요. 다시 말씀해주시면 곧바로 응답할게요 🙏"

        return {"reply": gemini_reply}
    except Exception as e:
        # 오류 메시지를 명확하게 Gemini 관련으로 변경합니다.
        print(f"❌ Gemini 응답 실패 (로그): {e}")
        return {"reply": f"❌ Gemini 응답 실패: {e}"}
