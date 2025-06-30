from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import google.generativeai as genai
import os

# Google Gemini API 키 설정: 환경 변수에서 불러옵니다.
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

import gspread
from google.oauth2.service_account import Credentials
import difflib
from sentence_transformers import SentenceTransformer, util
import torch

# SentenceTransformer 모델은 한 번만 로드하여 캐싱
# (이 부분이 전역으로 선언되어 함수 호출마다 로드되지 않도록 합니다.)
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
    threshold = 0.4 # 이 변수를 사용하고 있습니다.

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

    # for 루프가 끝난 후, 이 if/else 블록은 for 루프와 같은 들여쓰기 수준에 있어야 합니다.
    # 이전까지 이 부분이 잘못된 들여쓰기 오류를 유발했습니다.
    if best_match: # <<< 이 라인의 들여쓰기가 수정되었습니다.
        return {"reply": best_match["답변"]}
    else: # <<< 이 라인의 들여쓰기도 수정되었습니다.
        try:
            # Gemini 모델 초기화
            model = genai.GenerativeModel('gemini-pro')

            # Gemini에 보낼 시스템 프롬프트와 사용자 메시지를 결합합니다.
            full_prompt = (
                "당신은 KB손해보험 개인영업 설계사들을 도와주는 친절하고 유쾌한 여성 매니저 애순이입니다. "
                "사용자가 인삿말(예: '애순아', '안녕', '하이') 또는 일상적인 말을 하면 반드시 상냥하게 대답해 주세요. "
                "절대로 무응답하지 마세요. 보험 관련 질문이 아니어도 반드시 성의 있게 대답해 주세요.\n\n"
                f"사용자 질문: {request.message}"
            )

            # Gemini API가 요구하는 'contents' 형식으로 메시지 구성
            contents_message = [
                {
                    "role": "user",
                    "parts": [
                        full_prompt
                    ]
                }
            ]

            response = model.generate_content(
                contents_message,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )

            try: # 응답 추출을 위한 try-except 블록
                gemini_reply = response.text.strip() # .text 속성으로 응답 추출
                if not gemini_reply:
                    gemini_reply = "사장님, 어떤 도움이 필요하신가요? 😊"
            except Exception as e_extract: # 응답 추출 중 오류 처리
                print(f"❌ Gemini 응답 추출 실패 (로그): {e_extract}")
                gemini_reply = "애순이가 답변을 준비하지 못했어요. 다시 말씀해주시면 곧바로 응답할게요 🙏"

            return {"reply": gemini_reply}
        except Exception as e: # Gemini API 호출 자체의 오류 처리
            print(f"❌ Gemini 응답 실패 (로그): {e}")
            return {"reply": f"❌ Gemini 응답 실패: {e}"}