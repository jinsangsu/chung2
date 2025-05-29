
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
        @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic&display=swap');

        html, body, [class*="css"]  {
            font-family: 'Nanum Gothic', sans-serif !important;
        }

        div.block-container {
            padding-top: 3rem;
        }
        .aeson-container {
            display: flex;
            align-items: flex-start;
            gap: 2rem;
        }
        .aeson-text {
            margin-top: 0.5rem;
            font-size: 1.1rem;
            line-height: 1.7;
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
    <h3>사장님, 안녕하세요!</h3>
    저는 앞으로 사장님들 업무를 도와드리는<br>
    <b>충청호남본부 매니저봇 ‘애순’</b>이에요.<br><br>

    매니저님께 여쭤보시기 전에<br>
    저 애순이한테 먼저 물어봐 주세요!<br>
    제가 아는 건 바로, 친절하게 알려드릴게요!<br><br>

    사장님들이 더 빠르고, 더 편하게 영업하실 수 있도록<br>
    늘 옆에서 든든하게 함께하겠습니다.<br>
    <b>잘 부탁드려요! 😊</b>
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
    matched = []
    for _, row in df.iterrows():
        if row["질문"] and str(row["질문"]).strip() != "":
            if str(row["질문"]) in user_input or user_input in str(row["질문"]):
                matched.append(row)

    if len(matched) == 0:
        st.warning("애순이가 이해하지 못했어요. 다른 표현으로 다시 물어봐 주세요 😊")
    elif len(matched) == 1:
        st.success(matched[0]["답변"])
    else:
        st.info("다음 중 어떤 질문을 말씀하신 건가요?")
        for i, row in enumerate(matched, 1):
            st.write(f"{i}. {row['질문']}")
