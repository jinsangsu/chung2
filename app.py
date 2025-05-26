
import streamlit as st
import pandas as pd
import requests

# 구글시트 CSV URL
sheet_csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTFEGLsbl2td7NhCL5qkHeUvUxbXw6VgGHV6mcz4eVh_vN47HPz9JtU4id6VSPm2SKDJOufKNh5R5uZ/pub?output=csv"

# 시트 불러오기
@st.cache_data(ttl=600)
def load_qa_sheet():
    df = pd.read_csv(sheet_csv_url)
    return df.dropna()

qa_df = load_qa_sheet()

# 앱 설정
st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="centered")
st.markdown("<style>div.block-container{padding-top:3rem;}</style>", unsafe_allow_html=True)

# 상단 인사말 + 캐릭터
col1, col2 = st.columns([1, 5])
with col1:
    st.image("managerbot_character.webp", width=130)
with col2:
    st.markdown("#### **사장님, 안녕하세요!**")
    st.markdown("""저는 앞으로 사장님들 업무를 도와드리는  
**충청호남본부 매니저봇 ‘애순’**이에요.

매니저님께 여쭤보시기 전에  
저 애순이한테 먼저 물어봐 주세요!  
제가 아는 건 바로, 친절하게 알려드릴게요!

사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록  
늘 옆에서 든든하게 함께하겠습니다.  
**잘 부탁드려요! 😊**""")

st.markdown("---")

# 대화 기록 상태
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 기존 대화 출력
for q, a in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        st.markdown(a)

# 입력창
if prompt := st.chat_input("궁금한 내용을 입력해 주세요"):
    with st.chat_message("user"):
        st.markdown(prompt)

    # 키워드 기반 답변 탐색
    matched = None
    for _, row in qa_df.iterrows():
        if str(row["질문 키워드"]) in prompt:
            matched = row["답변"]
            break

    reply = matched if matched else "애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요 😊"

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat_history.append((prompt, reply))
