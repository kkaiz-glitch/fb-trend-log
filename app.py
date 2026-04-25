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
    '광고', '협찬', 'CU', '빵효진_cu', '빵효진_세븐일레븐', '공구', 'cu',
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
    st.title("매일유업 F&B 트렌드 인사이트")
    col_header1, col_header2 = st.columns([1, 1])
    with col_header1:
        st.caption(f"최종 업데이트 일자: {latest_date}")
    with col_header2:
        st.write(f"**수집된 인사이트:** 총 {len(df)}건 (최근 {len(latest_df)}건 추가됨)")

    # ---------------------------------------------------------
    # [수정 4 & 5] 상단: 오늘의 핵심 트렌드 요약 (가로로 길게)
    # ---------------------------------------------------------
    st.divider()
    st.info("오늘의 핵심 트렌드 요약")

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
        st.write("API 키를 설정하면 GPT의 자동 요약 결과가 여기에 표시됩니다.")

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
        st.success("해시태그 워드클라우드")

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
        st.warning("해시태그 TOP 10")
        
        if flat_tags:
            # 1. 오늘 집계
            today_counts = pd.Series(flat_tags).value_counts().reset_index()
            today_counts.columns = ['키워드', '오늘언급수']
            top_10 = today_counts.head(10).copy()

            try:
                all_dates = sorted(df['timestamp_kst'].unique())
                if len(all_dates) >= 2:
                    yesterday_date = all_dates[-2]
                    yesterday_df = df[df['timestamp_kst'] == yesterday_date]
                    
                    yesterday_tags_raw = yesterday_df['hashtags'].str.replace('[', '').str.replace(']', '').str.replace("'", "").str.split(', ')
                    yesterday_flat_tags = [
                        tag.strip() for sublist in yesterday_tags_raw.dropna() 
                        for tag in sublist if tag and tag.strip() not in STOPWORDS
                    ]
                    
                    yesterday_counts = pd.Series(yesterday_flat_tags).value_counts().reset_index()
                    yesterday_counts.columns = ['키워드', '어제언급수']
                    
                    # 데이터 병합
                    merged = pd.merge(top_10, yesterday_counts, on='키워드', how='left').fillna(0)
                    
                    # [로직 수정] 신규 진입 여부에 따른 라벨 및 증감률 처리
                    def get_new_label(row):
                        return "⭐ NEW" if row['어제언급수'] == 0 else ""

                    def get_change_rate(row):
                        # 전일 데이터가 0(NEW)이면 증감률을 계산하지 않고 공란("") 반환
                        if row['어제언급수'] == 0:
                            return "" 
                        
                        rate = ((row['오늘언급수'] - row['어제언급수']) / row['어제언급수']) * 100
                        prefix = "▲" if rate > 0 else ("▼" if rate < 0 else "")
                        
                        # 변화가 없으면 "-" 표시, 변화가 있으면 기호와 함께 수치 표시
                        return f"{prefix} {abs(rate):.0f}%" if prefix else "-"

                    merged['상태'] = merged.apply(get_new_label, axis=1)
                    merged['전일 대비(%)'] = merged.apply(get_change_rate, axis=1)
                    
                    # 최종 출력용 정리
                    final_table = merged[['상태', '키워드', '오늘언급수', '전일 대비(%)']]
                    final_table.columns = ['상태', '키워드', '언급수', '전일 대비(%)']
                else:
                    final_table = top_10.copy()
                    final_table['상태'] = ""
                    final_table['전일 대비(%)'] = ""
                    final_table = final_table[['상태', '키워드', '오늘언급수', '전일 대비(%)']]
                    final_table.columns = ['상태', '키워드', '언급수', '전일 대비(%)']
            
            except Exception as e:
                final_table = top_10.copy()
                final_table['상태'] = ""
                final_table['전일 대비(%)'] = ""
                final_table.columns = ['상태', '키워드', '언급수', '전일 대비(%)']

            # 표 출력
            st.dataframe(
                final_table,
                column_config={
                    "상태": st.column_config.TextColumn("NEW"), 
                    "키워드": st.column_config.TextColumn("키워드"),
                    "언급수": st.column_config.NumberColumn("언급수"),
                    "전일 대비(%)": st.column_config.TextColumn("전일대비(%)"),
                },
                hide_index=True,
                use_container_width=True  # 모든 열 너비를 화면에 맞춰 균등하게 배분
            )
        else:
            st.write("표시할 데이터가 없습니다.")


    # ---------------------------------------------------------
    # 하단: 기간별 트렌드 조회 (GPT 요약 우선 배치 버전)
    # ---------------------------------------------------------
    st.divider()
    st.subheader("기간별 트렌드 조회")
    
    # 1. 기간 선택 UI
    col_date1, col_date2 = st.columns([1, 1])
    min_date = df['timestamp_kst'].min()
    max_date = df['timestamp_kst'].max()
    
    with col_date1:
        start_date = st.date_input("시작일", min_date, min_value=min_date, max_value=max_date, key="start")
    with col_date2:
        end_date = st.date_input("종료일", max_date, min_value=min_date, max_value=max_date, key="end")

    # 기간 필터링
    filtered_df = df[(df['timestamp_kst'] >= start_date) & (df['timestamp_kst'] <= end_date)]

    if not filtered_df.empty:
        # 2. [신규] 선택 기간 GPT 핵심 요약
        st.write("")
        with st.expander(f"{start_date} ~ {end_date} 기간 트렌드 분석 리포트 (GPT)", expanded=True):
            if OPENAI_API_KEY != "sk-...":
                # 기간 내 게시물 캡션 결합
                period_context = "\n".join(filtered_df['caption'].dropna().astype(str).tolist())[:4000]
                
                @st.cache_data(ttl=3600)
                def get_period_summary(text):
                    client = OpenAI(api_key=OPENAI_API_KEY)
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "너는 F&B 시장 전략가야. 주어진 기간의 데이터를 분석해 소비자 반응과 마케팅 시사점을 전문적으로 요약해줘."},
                            {"role": "user", "content": f"다음은 {start_date}부터 {end_date}까지의 데이터야. 핵심 트렌드를 요약해줘.\n\n{text}"}
                        ]
                    )
                    return response.choices[0].message.content

                period_summary = get_period_summary(period_context)
                st.markdown(period_summary)
            else:
                st.write("API 키를 설정하면 기간별 분석이 표시됩니다.")

        # 3. BEST 게시물 (중간 배치)
        st.write("")
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            best_like = filtered_df.nlargest(1, 'likesCount').iloc[0]
            st.info(f"**기간 내 좋아요 BEST**\n\n@{best_like['ownerUsername']} (좋아요 {best_like['likesCount']}개)")
        with b_col2:
            best_comment = filtered_df.nlargest(1, 'commentsCount').iloc[0]
            st.warning(f"**기간 내 댓글 BEST**\n\n@{best_comment['ownerUsername']} (댓글 {best_comment['commentsCount']}개)")

        # 4. 전체 게시물 리스트 (가장 아래 배치)
        st.write("")
        st.write(f"**전체 게시물 리스트** ({len(filtered_df)}건)")
        st.dataframe(
            filtered_df[['ownerUsername', 'caption', 'likesCount', 'url']], 
            column_config={
                "ownerUsername": st.column_config.TextColumn("**계정**"),
                "caption": st.column_config.TextColumn("**내용**"),
                "likesCount": st.column_config.NumberColumn("**좋아요**"),
                "url": st.column_config.LinkColumn("**링크**")
            },
            height=400,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("선택하신 기간에 수집된 데이터가 없습니다.")
