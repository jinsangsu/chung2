
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import gspread
from google.oauth2.service_account import Credentials

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

@app.post("/chat")
async def chat(request: ChatRequest):
    if worksheet is None:
        return JSONResponse(content={"reply": "시트를 불러올 수 없습니다. 관리자에게 문의해주세요."})

    message = request.message.strip().lower()
    records = worksheet.get_all_records()
    matched = [r for r in records if message in r["질문"].lower()]

    if len(matched) == 0:
        return {"reply": "질문에 해당하는 답변을 찾을 수 없습니다."}
    elif len(matched) == 1:
        return {"reply": matched[0]['답변']}
    else:
        numbered_list = "\n".join([f"{i+1}. {r['질문']}" for i, r in enumerate(matched)])
        return {"reply": f"다음 중 어떤 질문에 대한 답변을 원하시나요?\n{numbered_list}"}
