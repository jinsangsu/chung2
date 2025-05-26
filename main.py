
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("aesoonkey.json", scope)
client = gspread.authorize(creds)

sheet = client.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
worksheet = sheet.worksheet("Sheet1")

def find_answer(user_input):
    try:
        records = worksheet.get_all_records()
        print(f"[시트에서 불러온 Q&A 수]: {len(records)}")
        for row in records:
            question = row.get("질문 내용", "")
            answer = row.get("답변 내용", "")
            print(f"[질문 비교]: '{question}' vs '{user_input}'")
            if question and question.strip() in user_input:
                return answer
            elif any(word in user_input for word in question.split()):
                return answer
        return "사장님~ 아직 이 질문에 대한 정보가 없어요! 시트에 추가해주시면 제가 더 공부할게요 😊"
    except Exception as e:
        print("[find_answer 내부 에러]", e)
        return "사장님~ 답변을 찾는 중 문제가 발생했어요. 충호해가 바로 고쳐볼게요!"

@app.post("/chat")
async def chat(request: Request):
    try:
        body = await request.json()
        user_input = body.get("message", "")
        print(f"[애순이 수신 질문] {user_input}")
        reply = find_answer(user_input)
        print(f"[애순이 응답 내용] {reply}")
        return JSONResponse(content={"reply": reply})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"reply": f"애순이 중계 서버 오류: {str(e)}"})
