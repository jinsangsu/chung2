from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# ✅ 예시 Q&A 리스트 (구글 시트에서 로딩한다고 가정)
qa_list = [
    {"question": "자동차 보험 가입 조건은?", "answer": "자동차 보험에 가입하려면 차량 등록증이 필요하며..."},
    {"question": "자동차 사고 시 대인 보상 절차는?", "answer": "자동차 사고 발생 시 대인 보상은 다음과 같이 진행됩니다..."},
    {"question": "자동차 보험 해지 방법은?", "answer": "보험 해지를 원하실 경우 고객센터를 통해..."},
    {"question": "화재 보험 가입 조건은?", "answer": "화재 보험은..."}
]

# ✅ 사용자 선택 대기 상태 저장 (user_id → [질문 리스트])
user_pending_selection = {}

class ChatRequest(BaseModel):
    user: str
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    user_input = request.message.strip()
    user_id = request.user

    # ✅ 이전 질문 선택 대기 중인 사용자 처리
    if user_id in user_pending_selection:
        options = user_pending_selection.pop(user_id)
        try:
            selection_index = int(user_input) - 1
            selected = options[selection_index]
            return {"reply": selected["answer"]}
        except (ValueError, IndexError):
            return {"reply": f"선택이 잘못되었습니다. 1~{len(options)} 사이의 번호를 입력해주세요."}

    # ✅ 사용자 입력 키워드와 관련된 질문 검색 (단순 포함 필터)
    matched = [qa for qa in qa_list if user_input in qa["question"]]

    if len(matched) == 0:
        return {"reply": "해당 내용에 대한 정보를 찾을 수 없습니다. 다른 질문을 입력해 주세요."}

    elif len(matched) == 1:
        return {"reply": matched[0]["answer"]}

    else:
        # ✅ 복수 질문 매칭 → 선택 유도
        response_text = f"'{user_input}'와 관련된 질문이 여러 개 있습니다. 어떤 항목이 궁금하신가요?\n"
        for idx, qa in enumerate(matched):
            response_text += f"{idx + 1}. {qa['question']}\n"
        response_text += "번호를 선택해 주세요."

        user_pending_selection[user_id] = matched
        return {"reply": response_text"}