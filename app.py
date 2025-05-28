import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 페이지 설정
st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="wide")

# 스타일 적용
st.markdown(
    """
    <style>
        div.block-container {
            padding-top: 3rem;
        }
        .aeson-container {
            display: flex;
            align-items: flex-start;
        }
        .aeson-text {
            margin-left: 3rem;
        }
        .aeson-img {
            flex-shrink: 0;
        }
    </style>
    """, unsafe_allow_html=True
)

# 웰컴 메시지 및 캐릭터 출력
st.markdown("<div class='aeson-container'>", unsafe_allow_html=True)
st.image("managerbot_character.webp", width=180)
st.markdown(
    """
    <div class='aeson-text'>
    ### 사장님, 안녕하세요!
    저는 앞으로 사장님들 업무를 도와드리는  
    **충청호남본부 매니저봇 ‘애순’**이에요.  

    매니저님께 여쭤보시기 전에  
    저 애순이한테 먼저 물어봐 주세요!  
    제가 아는 건 바로, 친절하게 알려드릴게요!  

    사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록  
    늘 옆에서 든든하게 함께하겠습니다.  
    **잘 부탁드려요! 😊**
    </div>
    """, unsafe_allow_html=True
)
st.markdown("</div>", unsafe_allow_html=True)

# 구글 시트 연동
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("singular-citron-459308-q0-5120c3914ca5.json", scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 사용자 질문 입력
user_input = st.text_input("궁금한 내용을 입력해 주세요", placeholder="예: 자동차 할인특약에는 어떤 것이 있나요?")

# 질문에 포함된 단어가 있는지 확인 후 응답
if user_input:
    found = False
    for _, row in df.iterrows():
        if row["질문"] and str(row["질문"]).strip() != "":
            if str(row["질문"]) in user_input:
                st.success(row["답변"])
                found = True
                break
    if not found:
        st.warning("애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요 😊")