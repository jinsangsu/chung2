
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()

# Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    "singular-citron-459308-q0-5120c3914ca5.json", scope
)
client = gspread.authorize(creds)

# Q&A 시트 불러오기
sheet = client.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ")
worksheet = sheet.sheet1

# 사용자 상태 저장
user_pending_selection = {}

class ChatRequest(BaseModel):
    user: str
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    user_input = request.message.strip()
    user_id = request.user or "default_user"

    # 이전 질문 선택 대기 중인 사용자 처리
    if user_id in user_pending_selection:
        options = user_pending_selection.pop(user_id)
        try:
            selection_index = int(user_input) - 1
            selected = options[selection_index]
            return {"reply": selected["answer"]}
        except (ValueError, IndexError):
            return {"reply": f"선택이 잘못되었습니다. 1~{len(options)} 사이의 번호를 입력해주세요."}

    # Google Sheet에서 Q&A 전체 불러오기
    all_data = worksheet.get_all_records()
    qa_list = [{"question": row["질문 내용"], "answer": row["답변 내용"]} for row in all_data if row["질문 내용"] and row["답변 내용"]]

    # 유연한 키워드 포함 매칭 (대소문자 무시)
    matched = [qa for qa in qa_list if user_input.lower() in qa["question"].lower()]

    if len(matched) == 0:
        return {"reply": "해당 내용에 대한 정보를 찾을 수 없습니다. 다른 질문을 입력해 주세요."}
    elif len(matched) == 1:
        return {"reply": matched[0]["answer"]}
    else:
        # 복수 질문 매칭 → 선택 유도
        response_text = f"'{user_input}'와 관련된 질문이 여러 개 있습니다. 어떤 항목이 궁금하신가요?\n"
        for idx, qa in enumerate(matched):
            response_text += f"{idx + 1}. {qa['question']}\n"
        response_text += "번호를 선택해 주세요."

        user_pending_selection[user_id] = matched
        return {"reply": response_text}
