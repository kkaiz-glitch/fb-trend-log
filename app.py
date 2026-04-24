import streamlit as st
import pandas as pd

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="F&B Trend Log", layout="wide")
st.title("📊 F&B Trend Log")

# 2. 데이터 불러오기
try:
    df = pd.read_csv("insta_trend_master.csv")
    
    # 사이드바 필터링
    st.sidebar.header("🗓️ 기간 선택")
    date_list = sorted(df['timestamp_kst'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("날짜를 선택하세요", date_list)

    # 데이터 필터링
    filtered_df = df[df['timestamp_kst'] == selected_date]

    # ---------------------------------------
    # 3. 상단 요약 지표 (Metrics)
    # ---------------------------------------
    st.subheader(f"📍 {selected_date} 마켓 리포트 요약")
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.metric("수집 게시물 수", f"{len(filtered_df)}건")
    with m2:
        avg_likes = int(filtered_df['likesCount'].mean())
        st.metric("평균 좋아요", f"{avg_likes}개")
    with m3:
        top_account = filtered_df.loc[filtered_df['likesCount'].idxmax(), 'ownerUsername']
        st.metric("베스트 계정", f"@{top_account}")

    st.divider()

    # ---------------------------------------
    # 4. 분석 영역 (인사이트 시각화)
    # ---------------------------------------
    col_left, col_right = st.columns([1.5, 1]) # 왼쪽을 좀 더 넓게

    with col_left:
        st.subheader("🔥 핵심 트렌드 게시물 (인게이지먼트 순)")
        # 좋아요 순으로 정렬해서 보여주기
        best_posts = filtered_df.sort_values(by='likesCount', ascending=False)
        st.dataframe(best_posts[['ownerUsername', 'caption', 'likesCount', 'url']], height=400)

    with col_right:
        st.subheader("📊 게시물 유형 비율")
        # 어떤 형태의 게시물이 많은지 차트로 보여줌
        type_counts = filtered_df['type'].value_counts()
        st.pie_chart(type_counts)
        
        st.subheader("🏷️ 주요 해시태그")
        # 해시태그 대충 나열해서 보여주기
        tags = filtered_df['hashtags'].str.replace('[', '').str.replace(']', '').str.replace("'", "").dropna()
        st.write(", ".join(tags.unique()[:20]))

except Exception as e:
    st.info("GitHub 저장소에 'insta_trend_master.csv' 파일을 업로드해 주세요! 에러가 발생했습니다: {e}")
