
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

    message = request.message.strip().lower()
    message_no_space = message.replace(" ", "")

    records = worksheet.get_all_records()
    best_match = None
    best_score = 0.0
    threshold = 0.55  # ✅ 의미 유사도 기준

    for r in records:
        q = r["질문"].strip().lower()
        q_no_space = q.replace(" ", "")

        # ✅ 문자열 포함 여부 먼저 확인
        if message in q or message_no_space in q_no_space:
            return {"reply": r["답변"]}

        # ✅ 의미 유사도 비교
        score1 = get_semantic_similarity(message, q)
        score2 = get_semantic_similarity(message_no_space, q_no_space)
        score3 = get_similarity_score(message, q)  # difflib 유사도

        final_score = max(score1, score2, score3)

        if final_score > threshold and final_score > best_score:
            best_match = r
            best_score = final_score

    if best_match:
        return {"reply": best_match["답변"]}
    else:
        return {"reply": "❌ 질문에 해당하는 답변을 찾을 수 없습니다."}
