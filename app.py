
import streamlit as st
import pandas as pd

st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="centered")
st.markdown("<style>div.block-container{padding-top:3rem;}</style>", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_qa_sheet():
    try:
        df = pd.read_csv("https://docs.google.com/spreadsheets/d/1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ/export?format=csv")
        return df[["질문 내용", "답변 내용"]].dropna()
    except Exception as e:
        st.error(f"❌ 구글시트를 불러오지 못했습니다: {e}")
        return pd.DataFrame(columns=["질문 내용", "답변 내용"])

qa_df = load_qa_sheet()

# 상단 인사말
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

# 대화 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 대화 출력
for q, a in st.session_state.chat_history:
    with st.chat_message("user"):
        st.markdown(q)
    with st.chat_message("assistant"):
        st.markdown(a)

# 입력창
if prompt := st.chat_input("궁금한 내용을 입력해 주세요"):
    with st.chat_message("user"):
        st.markdown(prompt)

    # 질문 찾기
    match = None
    for _, row in qa_df.iterrows():
        if str(row["질문 내용"]).strip() in prompt:
            match = str(row["답변 내용"]).strip()
            break

    reply = match if match else "애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요 😊"

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.session_state.chat_history.append((prompt, reply))
