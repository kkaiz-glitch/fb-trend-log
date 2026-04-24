import streamlit as st
import pandas as pd

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="F&B Trend Log", layout="wide")
st.title("📊 F&B Trend Log")

# 2. 데이터 불러오기
try:
    # 파일을 읽어올 때 문자열로 명확히 처리
    df = pd.read_csv("insta_trend_master.csv")
    
    # 사이드바 필터링
    st.sidebar.header("🗓️ 기간 선택")
    
    # 날짜 컬럼이 있는지 확인하고 정렬
    if 'timestamp_kst' in df.columns:
        date_list = sorted(df['timestamp_kst'].dropna().unique(), reverse=True)
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
            avg_likes = int(filtered_df['likesCount'].mean()) if not filtered_df.empty else 0
            st.metric("평균 좋아요", f"{avg_likes}개")
        with m3:
            if not filtered_df.empty:
                top_account = filtered_df.loc[filtered_df['likesCount'].idxmax(), 'ownerUsername']
                st.metric("베스트 계정", f"@{top_account}")
            else:
                st.metric("베스트 계정", "데이터 없음")

        st.divider()

        # ---------------------------------------
        # 4. 분석 영역 (인사이트 시각화)
        # ---------------------------------------
        col_left, col_right = st.columns([1.5, 1])

        with col_left:
            st.subheader("🔥 핵심 트렌드 게시물")
            best_posts = filtered_df.sort_values(by='likesCount', ascending=False)
            st.dataframe(best_posts[['ownerUsername', 'caption', 'likesCount', 'url']], height=400)

        with col_right:
            st.subheader("📊 게시물 유형 분석")
            # pie_chart 대신 기본 bar_chart 사용 (Streamlit 기본 내장)
            type_counts = filtered_df['type'].value_counts()
            st.bar_chart(type_counts)
            
            st.subheader("🏷️ 주요 해시태그")
            # 해시태그 정리
            if 'hashtags' in filtered_df.columns:
                tags = filtered_df['hashtags'].astype(str).str.replace('[', '').str.replace(']', '').str.replace("'", "").dropna()
                st.write(", ".join(tags.unique()[:20]))
    else:
        st.error("CSV 파일에 'timestamp_kst' 컬럼이 없습니다. 파일 형식을 확인해주세요!")

except Exception as e:
    st.error(f"에러가 발생했습니다: {e}")
