import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from openai import OpenAI
from wordcloud import WordCloud
import os
import matplotlib.pyplot as plt

# 1. 페이지 설정
st.set_page_config(page_title="F&B 트렌드 인사이트", layout="wide")

# --- 설정 (마케터님의 API 키를 입력하세요) ---
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"] 

#제외 해시태그
STOPWORDS = [
    '광고', '협찬', 'CU', '빵효진_cu', '빵효진_세븐일레븐', '공구', 
    '체험단', '서포터즈', '인스타그램', '팔로우', '좋아요', 'nan', '일상', '소통'
]

# 2. 데이터 로드 함수
@st.cache_data
def load_data():
    df = pd.read_csv("insta_trend_master.csv")
    df['timestamp_kst'] = pd.to_datetime(df['timestamp_kst']).dt.date
    return df

try:
    df = load_data()
    
    # [수정 1] 전일(최근 데이터) 기준 상단 요약용 데이터 추출
    latest_date = df['timestamp_kst'].max()
    latest_df = df[df['timestamp_kst'] == latest_date]
    
    # [수정 3] 상단 타이틀 및 수집 인사이트 건수 표시
    st.title("📊 F&B 트렌드 인사이트")
    col_header1, col_header2 = st.columns([1, 1])
    with col_header1:
        st.caption(f"최종 업데이트 일자: {latest_date}")
    with col_header2:
        st.write(f"🔍 **수집된 인사이트:** 총 {len(df)}건 (최근 {len(latest_df)}건 추가됨)")

    # ---------------------------------------------------------
    # [수정 4 & 5] 상단: 오늘의 핵심 트렌드 요약 (가로로 길게)
    # ---------------------------------------------------------
    st.divider()
    st.info("🔥 오늘의 핵심 트렌드 요약")

    # GPT 분석 로직
    if OPENAI_API_KEY != "sk-...":
        client = OpenAI(api_key=OPENAI_API_KEY)
        # 최근 게시물 캡션들을 결합 (최대 3000자)
        context = "\n".join(latest_df['caption'].dropna().astype(str).tolist())[:3000]

        # 1. GPT에게 보낼 텍스트를 만들 때 링크 정보를 포함시킵니다.
        # (get_gpt_summary 함수 윗부분이나 호출 직전에 배치)
        context_list = []
        for _, row in latest_df.iterrows():
            # 계정과 URL을 결합한 참조 정보 생성
            ref = f"[출처: @{row['ownerUsername']}]({row['url']})"
            context_list.append(f"계정: {row['ownerUsername']}\n내용: {row['caption']}\n참조링크: {ref}")
        
        context = "\n\n---\n\n".join(context_list)[:4000] # 텍스트 결합
        
        @st.cache_data(ttl=3600)
        def get_gpt_summary(text):
            # 1. 시스템 프롬프트 (GPT의 페르소나와 규칙 설정)
            system_prompt = """
            너는 데이터 기반의 F&B 트렌드 분석가이자 시장 전략가야. 
            인스타그램 데이터를 분석하여, 마케팅 결정권자가 실무 전략 수립에 즉시 참고할 수 있는 내용을 작성해야 해.
        
            [작성 원칙]
            1. 현재 데이터에서 가장 두드러지는 핵심 현상을 중심으로 직접 카테고리를 생성할 것.
            2. 모든 분석 결과는 철저히 비즈니스적 관점에서 논리적이고 전문적인 어조로 작성할 것.
            3. 각 분석 섹션에는 근거가 되는 게시물의 출처를 반드시 포함해야 함. [출처: @계정명](URL) 형식을 지켜 마우스 클릭 시 바로 이동할 수 있게 할 것.
            """
        
            # 2. 유저 프롬프트 (실제 분석할 데이터와 형식 지정)
            user_prompt = f"""
            다음은 인스타그램에서 추출한 최신 F&B 관련 데이터야. 
            이 데이터를 카테고라이징하여 마케팅 관점에서 일목요연하게 설명해줘.
        
            [입력 데이터]
            {text}

            [출처 표시 예시]
            [@계정명](https://www.instagram.com/p/abcde/)
            """
        
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.choices[0].message.content

        summary_result = get_gpt_summary(context)
        st.markdown(summary_result)
    else:
        st.write("💡 API 키를 설정하면 GPT의 자동 요약 결과가 여기에 표시됩니다.")

    # ---------------------------------------------------------
    # [수정 5] 중단: 해시태그 섹션 (좌: 워드클라우드 / 우: TOP 10)
    # ---------------------------------------------------------
    st.write("") # 간격 조절
    mid1, mid2 = st.columns([1, 1])

    # 해시태그 정제
    all_tags = latest_df['hashtags'].str.replace('[', '').str.replace(']', '').str.replace("'", "").str.split(', ')
    flat_tags = [
        tag for sublist in all_tags.dropna() 
        for tag in sublist 
        if tag and (tag not in STOPWORDS) and (tag.replace('#', '') not in STOPWORDS)
    ]

    with mid1:
        st.success("☁️ 해시태그 워드클라우드")

        def black_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
            return "rgb(0, 0, 0)"  # 검은색 RGB 값
        
        if flat_tags:
            text_for_wc = " ".join(flat_tags)
            
            # [수정] 현재 파일의 경로를 기준으로 폰트 위치를 정확히 잡습니다.
            current_path = os.path.dirname(os.path.abspath(__file__))
            font_file = os.path.join(current_path, 'NanumGothic-Regular.ttf')
            
            try:
                # 폰트 파일이 실제로 존재하는지 한 번 더 확인하는 로직
                if os.path.exists(font_file):
                    wc = WordCloud(
                        font_path=font_file,  # 절대 경로로 지정
                        width=800, 
                        height=600, 
                        background_color='white',  # 배경은 흰색
                        prefer_horizontal=0.8,
                        color_func=black_color_func
                    ).generate(text_for_wc)
                    
                    fig, ax = plt.subplots(figsize=(10, 8))
                    ax.imshow(wc, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                else:
                    # 폰트 파일이 경로상에 없을 때 에러 메시지 출력
                    st.error(f"폰트 파일을 찾을 수 없습니다: {font_file}")
                    st.write(", ".join(list(set(flat_tags))[:25]))
                    
            except Exception as e:
                st.warning(f"워드클라우드 생성 중 오류 발생: {e}")
                st.write(", ".join(list(set(flat_tags))[:25]))
        else:
            st.write("분석할 해시태그 데이터가 없습니다.")

    with mid2:
        st.warning("🔝 해시태그 TOP 10")
        tag_counts = pd.Series(flat_tags).value_counts().head(10).reset_index()
        tag_counts.columns = ['키워드', '언급수']
        st.table(tag_counts)

    # ---------------------------------------------------------
    # 하단: 날짜별 상세 데이터 분석 (기존 기능 유지)
    # ---------------------------------------------------------
    st.divider()
    st.subheader("🔍 기간별 상세 데이터 조회")
    
    # 사이드바에서 날짜 선택
    date_list = sorted(df['timestamp_kst'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("상세 정보를 볼 날짜를 선택하세요", date_list)
    filtered_df = df[df['timestamp_kst'] == selected_date]

    b1, b2, b3 = st.columns([2, 1, 1])
    with b1:
        st.write(f"📅 **{selected_date}**의 전체 게시물")
        st.dataframe(filtered_df[['ownerUsername', 'caption', 'likesCount', 'url']], height=300)
    with b2:
        st.write("❤️ 좋아요 BEST")
        if not filtered_df.empty:
            best = filtered_df.nlargest(1, 'likesCount').iloc[0]
            st.info(f"@{best['ownerUsername']}\n\n좋아요 {best['likesCount']}개")
    with b3:
        st.write("💬 댓글 BEST")
        if not filtered_df.empty:
            best = filtered_df.nlargest(1, 'commentsCount').iloc[0]
            st.warning(f"@{best['ownerUsername']}\n\n댓글 {best['commentsCount']}개")

except Exception as e:
    st.error(f"데이터를 읽어오는 중 오류가 발생했습니다: {e}")
