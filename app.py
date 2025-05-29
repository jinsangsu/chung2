
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 설정
st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="wide")

# 스타일 적용
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap');
        html, body, [class*="css"] {
            font-family: 'Nanum Gothic', sans-serif !important;
        }
        div.block-container {
            padding-top: 2rem;
        }
        .aeson-text {
            font-size: 1.05rem;
            line-height: 1.8;
        }
        .aeson-text h2 {
            font-size: 1.6rem;
            font-weight: bold;
        }
        .aeson-text p {
            margin: 0.4rem 0;
        }
        .response-box {
            background-color: #f9f9f9;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# 상단 UI - col 구조
col1, col2 = st.columns([1, 3])
with col1:
    st.image("managerbot_character.webp", width=180)
with col2:
    st.markdown("""
        <div class='aeson-text'>
            <h2>사장님, 안녕하세요!</h2>
            <p>저는 앞으로 사장님들 업무를 도와드리는</p>
            <p><span style="font-weight:bold">충청호남본부 매니저봇 '애순'</span>이에요.</p>
            <p>매니저님께 여쭤보시기 전에<br>
            저 애순이한테 먼저 물어봐 주세요!<br>
            제가 아는 건 바로, 친절하게 알려드릴게요!</p>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
            늘 옆에서 든든하게 함께하겠습니다.</p>
            <p><span style="font-weight:bold">잘 부탁드려요!</span></p>
        </div>
    """, unsafe_allow_html=True)

# 구글 시트 연동
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("singular-citron-459308-q0-5120c3914ca5.json", scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
df = pd.DataFrame(sheet.get_all_records())

# 질문 입력창 고정
st.markdown("---")
user_input = st.text_input("궁금한 내용을 입력해 주세요", key="question_input", placeholder="예: 자동이체 방법", label_visibility="visible")

# 응답 처리
if user_input:
    matched = []
    for _, row in df.iterrows():
        if str(row["질문"]).strip() and (row["질문"] in user_input or user_input in row["질문"]):
            matched.append(row)

    st.markdown("<div class='response-box'>", unsafe_allow_html=True)
    if len(matched) == 0:
        st.warning("애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요.")
    elif len(matched) == 1:
        st.success(matched[0]["답변"])
    else:
        st.info("다음 중 어떤 질문을 말씀하신 건가요?")
        for i, row in enumerate(matched, 1):
            st.write(f"{i}. {row['질문']}")
    st.markdown("</div>", unsafe_allow_html=True)
