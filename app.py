import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 페이지 설정
st.set_page_config(page_title="애순이 매니저봇", page_icon="🧡", layout="centered")

# 스타일 설정
st.markdown(
    """
    <style>
    div.block-container {padding-top:3rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

# 상단 레이아웃: 캐릭터 이미지 + 텍스트
col1, col2 = st.columns([1, 2])
with col1:
    st.image("managerbot_character.webp", width=180)
with col2:
    st.markdown("### 사장님, 안녕하세요!")
    st.markdown("저는 앞으로 사장님들 업무를 도와드리는  
**충청호남본부 매니저봇 ‘애순’**이에요.")
    st.markdown(
        "매니저님께 여쭤보시기 전에  
저 애순이한테 먼저 물어봐 주세요!  
제가 아는 건 바로, 친절하게 알려드릴게요!"
    )
    st.markdown(
        "사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록  
늘 옆에서 든든하게 함께하겠습니다.  
**잘 부탁드려요! 😊**"
    )

# 구글 시트 연동
@st.cache_data(ttl=60)
def load_qa_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "singular-citron-459308-q0-5120c3914ca5.json", scope
    )
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

try:
    qa_df = load_qa_sheet()
except Exception as e:
    st.error("❌ 구글시트를 불러오지 못했습니다: " + str(e))
    st.stop()

# 질문 입력
user_question = st.text_input("궁금한 내용을 입력해 주세요", key="input")

# 응답 처리
if user_question:
    match_found = False
    for _, row in qa_df.iterrows():
        if row["질문"] and str(row["질문"]).strip() in user_question:
            st.success(row["답변"])
            match_found = True
            break
    if not match_found:
        st.warning("애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요 😊")
