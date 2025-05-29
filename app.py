
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="애순이 매니저봇", page_icon="💛", layout="wide")

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap');
        html, body, [class*="css"] {
            font-family: 'Nanum Gothic', sans-serif !important;
        }
        div.block-container {
            padding-top: 3rem;
        }
        .aeson-text {
            font-size: 1.05rem;
            line-height: 1.8;
        }
        .aeson-text h2 {
            font-size: 1.6rem;
            font-weight: bold;
            margin-bottom: 0.8rem;
        }
        .aeson-text p {
            margin: 0.3rem 0;
        }
    </style>
    """, unsafe_allow_html=True
)

# 2단 컬럼 구성 (이미지 왼쪽, 텍스트 오른쪽)
col1, col2 = st.columns([1, 3])
with col1:
    st.image("managerbot_character.webp", width=180)

with col2:
    st.markdown(
        """
        <div class='aeson-text'>
            <h2>사장님, 안녕하세요!</h2>
            <p>저는 앞으로 사장님들 업무를 도와드리는</p>
            <p><span style="font-weight:bold">충청호남본부 매니저봇 '애순'</span>이에요.</p>
            <br>
            <p>매니저님께 여쭤보시기 전에<br>
            저 애순이한테 먼저 물어봐 주세요!<br>
            제가 아는 건 바로, 친절하게 알려드릴게요!</p>
            <br>
            <p>사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
            늘 옆에서 든든하게 함께하겠습니다.</p>
            <p><span style="font-weight:bold">잘 부탁드려요!</span></p>
        </div>
        """, unsafe_allow_html=True
    )

# 구글시트 연동 및 응답 로직
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("singular-citron-459308-q0-5120c3914ca5.json", scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_key("1rJdNc_cYw3iOkOWCItjgRLw-EqjqImkZ").worksheet("질의응답시트")
data = sheet.get_all_records()
df = pd.DataFrame(data)

user_input = st.text_input("궁금한 내용을 입력해 주세요", placeholder="예: 자동차 할인특약에는 어떤 것이 있나요?")

if user_input:
    matched = []
    for _, row in df.iterrows():
        if row["질문"] and str(row["질문"]).strip() != "":
            if str(row["질문"]) in user_input or user_input in str(row["질문"]):
                matched.append(row)

    if len(matched) == 0:
        st.warning("애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요.")
    elif len(matched) == 1:
        st.success(matched[0]["답변"])
    else:
        st.info("다음 중 어떤 질문을 말씀하신 건가요?")
        for i, row in enumerate(matched, 1):
            st.write(f"{i}. {row['질문']}")
