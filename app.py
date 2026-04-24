import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. 페이지 설정 (넓게 사용)
st.set_page_config(page_title="F&B 트렌드 인사이트", layout="wide")

# 타이틀 및 업데이트 일자
st.title("📊 F&B 트렌드 인사이트")
st.caption(f"최종 업데이트 일자: {datetime.now().strftime('%Y-%m-%d')}")

# 2. 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv("insta_trend_master.csv")
    df['timestamp_kst'] = pd.to_datetime(df['timestamp_kst']).dt.date
    return df

try:
    df = load_data()

    # 3. 사이드바 - 날짜 선택 (기획안의 DATE 시작/종료일)
    st.sidebar.header("🗓️ 기간 설정")
    min_date = df['timestamp_kst'].min()
    max_date = df['timestamp_kst'].max()
    
    start_date, end_date = st.sidebar.date_input(
        "분석 기간을 선택하세요",
        value=(max_date - timedelta(days=1), max_date),
        min_value=min_date,
        max_value=max_date
    )

    # 데이터 필터링
    filtered_df = df[(df['timestamp_kst'] >= start_date) & (df['timestamp_kst'] <= end_date)]

    # ---------------------------------------------------------
    # 4. 상단 3단 섹션 (요약 / 워드클라우드 / TOP 10)
    # ---------------------------------------------------------
    t1, t2, t3 = st.columns([1.5, 1, 1.2], gap="large")

    with t1:
        st.info("💡 오늘의 핵심 트렌드 요약")
        st.markdown(f"""
        - **분석 기간:** {start_date} ~ {end_date}
        - **수집된 인사이트:** 총 {len(filtered_df)}건의 게시물 분석 완료
        - **핵심 요약:** 이 영역은 GPT-4o 분석 결과나 대표 캡션을 넣기에 좋습니다. 
        """)
        # 팁: GPT 분석 결과가 있다면 여기에 텍스트로 넣어주면 됩니다.

    with t2:
        st.success("☁️ 급상승 해시태그 (워드클라우드 대용)")
        # 워드클라우드 대신 간단한 태그 클라우드 시각화
        all_tags = filtered_df['hashtags'].str.replace('[', '').str.replace(']', '').str.replace("'", "").str.split(', ')
        flat_tags = [tag for sublist in all_tags.dropna() for tag in sublist if tag and tag != 'nan']
        st.write(", ".join(list(set(flat_tags))[:30])) # 주요 태그 30개 나열

    with t3:
        st.warning("🔝 해시태그 TOP 10")
        tag_counts = pd.Series(flat_tags).value_counts().head(10).reset_index()
        tag_counts.columns = ['키워드', '언급수']
        st.table(tag_counts) # 순위 표

    st.divider()

    # ---------------------------------------------------------
    # 5. 하단 섹션 (해당 날짜 요약 / 반응도 높은 게시물)
    # ---------------------------------------------------------
    b1, b2, b3 = st.columns([2, 1, 1], gap="medium")

    with b1:
        st.subheader("📝 해당 기간 기준 트렌드 요약")
        # 가장 좋아요가 많은 게시물의 캡션을 요약으로 보여줌
        if not filtered_df.empty:
            top_insight = filtered_df.sort_values(by='likesCount', ascending=False).iloc[0]['caption']
            st.markdown(f"> {top_insight[:300]}...")
        else:
            st.write("데이터가 없습니다.")

    with b2:
        st.subheader("❤️ 좋아요 가장 많은 게시물")
        if not filtered_df.empty:
            best_like = filtered_df.nlargest(1, 'likesCount')
            st.write(f"@{best_like.iloc[0]['ownerUsername']}")
            st.write(f"좋아요: {best_like.iloc[0]['likesCount']}개")
            st.link_button("게시물 보기", best_like.iloc[0]['url'])

    with b3:
        st.subheader("💬 댓글 가장 많은 게시물")
        if not filtered_df.empty:
            best_comm = filtered_df.nlargest(1, 'commentsCount')
            st.write(f"@{best_comm.iloc[0]['ownerUsername']}")
            st.write(f"댓글: {best_comm.iloc[0]['commentsCount']}개")
            st.link_button("게시물 보기", best_comm.iloc[0]['url'])

except Exception as e:
    st.error(f"데이터를 불러오는 중 에러가 발생했습니다: {e}")
