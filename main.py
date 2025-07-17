import torch
from sentence_transformers import SentenceTransformer, util
import difflib
from google.oauth2.service_account import Credentials
import gspread
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai
import os

# Google Gemini API 키 설정: 환경 변수에서 불러옵니다.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("✅ GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

# SentenceTransformer 모델은 한 번만 로드하여 캐싱
model = SentenceTransformer('paraphrase-MiniLM-L6-v2')


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
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
try:
    creds = Credentials.from_service_account_file(
        "aesoonkey.json", scopes=scope)
    client = gspread.authorize(creds)
    worksheet = client.open_by_key(
        "1aPo40QnxQrcY7yEUM6iHa-9XJU-MIIqsjapGP7UnKIo").worksheet("질의응답시트")
except Exception as e:
    print("❌ Google Sheet 연결 실패:", e)
    worksheet = None


class ChatRequest(BaseModel):
    message: str


def get_similarity_score(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


SIMILARITY_THRESHOLD = 0.4

async def ask_gemini(user_message: str):
    try:
        model = genai.GenerativeModel(model_name="models/gemini-pro")
        full_prompt = (
            "당신은 KB손해보험 개인영업 설계사들을 도와주는 친절하고 유쾌한 여성 매니저 애순이입니다. "
            "사용자가 인삿말(예: '애순아', '안녕', '하이') 또는 일상적인 말을 하면 반드시 상냥하게 대답해 주세요. "
            "절대로 무응답하지 마세요. 보험 관련 질문이 아니어도 반드시 성의 있게 대답해 주세요.\n\n"
            f"사용자 질문: {user_message}"
        )
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        if hasattr(response, "text"):
            return {"reply": response.text.strip()}
        else:
            return {"reply": "🧠 Gemini가 답변을 찾지 못했어요."}
    except Exception as e:
        return {"reply": f"❌ Gemini API 호출 실패: {e}"}


@app.post("/chat")
async def chat(request: ChatRequest):
    if worksheet is None:
        return JSONResponse(content={"reply": "시트를 불러올 수 없습니다. 관리자에게 문의해주세요."})
    
    greetings = ["안녕", "하이", "애순아", "반가워", "몇살", "누구야", "이름", "자기소개", "뭐야", "있어?"]
    if any(greet in request.message.lower() for greet in greetings):
        return await ask_gemini(request.message)

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
        

        final_score = max(score1, score2)

        if final_score > 0.6 and final_score > best_score:
            best_match = r
            best_score = final_score

    # ✅ 유사 질문이 있을 경우
    if best_match:
        return {"reply": best_match["답변"]}

    # ✅ 유사 질문이 없을 경우: Gemini로 처리
    try:
        print("✅ Gemini 응답 호출 시작")
        return await ask_gemini(request.message)
    except Exception as e:
        print(f"❌ Gemini API 호출 실패: {e}")
        return {"reply": f"❌ Gemini API 호출 실패: {e}"}