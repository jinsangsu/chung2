
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")



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
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 KB손해보험 개인영업 설계사들을 도와주는 친절하고 유쾌한 여성 매니저 애순이입니다. 사용자가 인삿말(예: '애순아', '안녕', '하이') 또는 일상적인 말을 하면 반드시 상냥하게 대답해 주세요. 절대로 무응답하지 마세요. 보험 관련 질문이 아니어도 반드시 성의 있게 대답해 주세요."},
                    {"role": "user", "content": request.message}
                ],
                temperature=0.7
            )
            if completion and completion.choices and "message" in completion.choices[0] and "content" in completion.choices[0].message:
                gpt_reply = completion.choices[0].message.content.strip()
                if not gpt_reply:
                    gpt_reply = "사장님, 어떤 도움이 필요하신가요? 😊"
            else:
                gpt_reply = "애순이가 잠시 자리를 비운 것 같아요. 다시 말씀해주시면 곧바로 응답할게요 🙏"

            return {"reply": gpt_reply}
        except Exception as e:
            print(f"❌ GPT 응답 실패 (로그): {e}")
            return {"reply": f"❌ GPT 응답 실패: {e}"}

