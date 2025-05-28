
from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi.responses import JSONResponse

app = FastAPI()

# CORS 허용 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 구글 시트 연동 설정
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("gspread_key.json", scope)
client = gspread.authorize(creds)

worksheet = None
try:
    sheet = client.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
    worksheet = sheet.sheet1
except Exception as e:
    print("❌ Google Sheet 연결 실패:", e)

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    if worksheet is None:
        return JSONResponse(content={"reply": "시트를 불러올 수 없습니다. 관리자에게 문의해주세요."})

    message = request.message.strip()

    records = worksheet.get_all_records()
    matched = [r for r in records if message in r['질문']]

    if len(matched) == 0:
        return {"reply": "질문에 해당하는 답변을 찾을 수 없습니다."}
    elif len(matched) == 1:
        return {"reply": matched[0]['답변']}
    else:
        numbered_list = "\n".join([f"{i+1}. {r['질문']}" for i, r in enumerate(matched)])
        return {"reply": f"다음 중 어떤 질문에 대한 답변을 원하시나요?\n{numbered_list}"}
