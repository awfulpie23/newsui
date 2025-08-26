import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- 페이지 기본 설정 ---
st.set_page_config(layout="wide")

# --- 기본 스타일 설정 (모던한 UI를 위한 CSS) ---
st.markdown("""
<style>
    /* 기본 폰트 및 배경 설정 */
    html, body, [class*="st-"] {
        font-family: 'Nanum Gothic', sans-serif;
    }
    /* 버튼 스타일 */
    .stButton>button {
        border-radius: 5px;
        padding: 10px 15px;
        border: 1px solid #00408B;
        background-color: #FFFFFF;
        color: #00408B;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #00408B;
        color: white;
        border-color: #00408B;
    }
    /* 컨테이너 스타일 */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stVerticalBlock"] {
        border: 1px solid #EAECEE;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# --- 데이터 로드 및 전처리 함수 ---
@st.cache_data
def load_data(uploaded_file):
    """
    업로드된 파일을 읽어 데이터프레임으로 변환하고 기본 전처리를 수행합니다.
    Streamlit의 캐시 기능을 사용하여 파일 내용이 변경될 때만 새로 로드합니다.
    """
    if uploaded_file is None:
        return pd.DataFrame() # 파일이 없으면 빈 데이터프레임 반환
    try:
        # 파일 이름 확장자로 엑셀/CSV 구분
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        else: # .csv 또는 다른 텍스트 기반 파일
            df = pd.read_csv(uploaded_file)
            
        # 날짜 형식 변환
        df['news_bas_dt'] = pd.to_datetime(df['news_bas_dt'], format='%Y%m%d', errors='coerce')
        # '오전'/'오후'가 포함된 날짜 형식 처리를 위해 문자열을 먼저 변환합니다.
        # 예: '2025.08.06. 오전 7:14' -> '2025.08.06. AM 7:14'
        temp_dates = df['news_cr_pub_date'].astype(str).str.replace('오전', 'AM').str.replace('오후', 'PM')
        df['news_cr_pub_date'] = pd.to_datetime(temp_dates, format='%Y.%m.%d. %p %I:%M', errors='coerce')
        df.dropna(subset=['news_bas_dt'], inplace=True)

        # 결측치 처리
        fill_na_cols = {
            'news_cr_press': '출처 없음',
            'news_link': '',
            'news_cr_title': '제목 없음',
            'news_cr_content': '내용 없음',
            'news_title_by_agent': '요약 제목 없음',
            'news_text_by_agent': '요약 내용 없음'
        }
        df.fillna(fill_na_cols, inplace=True)
        return df
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# --- 최상단 제목 ---
st.markdown("<h1 style='text-align: center; color: #00408B;'>우리금융 서울대 AI/데이터 3조 : 테마별 뉴스 요약 서비스</h1>", unsafe_allow_html=True)
st.markdown("---")

# --- 상단 컨트롤 (파일 업로드) ---
uploaded_file = st.file_uploader("엑셀 또는 CSV 파일을 업로드하세요", type=['xlsx', 'csv'])

# --- 데이터 로드 ---
df = load_data(uploaded_file)

if df.empty:
    st.info("뉴스 데이터를 보려면 엑셀 또는 CSV 파일을 업로드해주세요.")
    st.stop()

# --- 데이터 로드 후 컨트롤 (날짜 선택, 조회) ---
# 데이터가 로드된 후, 데이터의 실제 날짜 범위를 기본값으로 설정
min_date_in_data = df['news_bas_dt'].min().date()
max_date_in_data = df['news_bas_dt'].max().date()

header_cols = st.columns([2, 2, 1])
with header_cols[0]:
    start_date_input = st.date_input('시작일', value=min_date_in_data, min_value=min_date_in_data, max_value=max_date_in_data)
with header_cols[1]:
    end_date_input = st.date_input('종료일', value=max_date_in_data, min_value=min_date_in_data, max_value=max_date_in_data)
with header_cols[2]:
    st.write("") # 조회 버튼과 높이를 맞추기 위한 여백
    st.write("")
    search_button = st.button('조회')

# 날짜 필터링
filtered_df = df[(df['news_bas_dt'].dt.date >= start_date_input) & (df['news_bas_dt'].dt.date <= end_date_input)]

# --- 메인 화면 4분할 ---
main_cols = st.columns([0.15, 0.15, 0.35, 0.35])

# --- 1컬럼: 날짜 ---
with main_cols[0]:
    st.header("날짜")
    unique_dates = sorted(filtered_df['news_bas_dt'].dt.date.unique(), reverse=True)
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = None

    for date in unique_dates:
        # 선택된 날짜는 다른 스타일로 표시
        if st.session_state.selected_date == date:
            st.markdown(f"""
            <div style="
                background-color: #00408B; 
                color: white; 
                padding: 10px 15px; 
                border-radius: 5px; 
                text-align: center;
                margin: 0.25rem 0;
                border: 1px solid #00408B;
            ">
                {date.strftime('%Y-%m-%d')}
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button(date.strftime('%Y-%m-%d'), key=f"date_{date}", use_container_width=True):
                # 날짜를 클릭하면 해당 날짜로 필터링
                st.session_state.selected_date = date

    # 선택된 날짜가 있으면 데이터프레임 추가 필터링
    if st.session_state.selected_date:
        filtered_df = filtered_df[filtered_df['news_bas_dt'].dt.date == st.session_state.selected_date]


# --- 2컬럼: 테마 ---
with main_cols[1]:
    st.header("테마")
    # 필터링된 데이터의 테마 목록 생성
    themes = ['전체'] + sorted(list(filtered_df['theme_name'].unique()))
    selected_theme = st.radio("테마를 선택하세요", themes, key="theme_selector")

# 테마 필터링 적용
if selected_theme != '전체':
    filtered_df = filtered_df[filtered_df['theme_name'] == selected_theme]


# --- 3컬럼: 요약 ---
with main_cols[2]:
    st.header(f"뉴스 요약 ({len(filtered_df)}개)")
    summary_container = st.container(height=600, border=False)
    
    # 세션 상태에 선택된 기사 인덱스 초기화
    if 'selected_article_index' not in st.session_state:
        st.session_state.selected_article_index = None

    with summary_container:
        # 날짜 최신순으로 정렬하여 표시
        for index, row in filtered_df.sort_values(by='news_cr_pub_date', ascending=False).iterrows():
            # 각 기사를 별도의 컨테이너에 담아 영역 구분
            with st.container():
                # ** 마우스 롤오버(Hover) 효과 구현 **
                # Streamlit은 직접적인 Hover 이벤트를 지원하지 않습니다.
                # 가장 유사한 경험을 제공하기 위해, 버튼 클릭으로 기사 내용을 표시합니다.
                # 사용자가 '내용 보기'를 누르면 오른쪽에 원문이 나타납니다.
                st.markdown(f"**{row['news_title_by_agent']}**")
                pub_date_str = row['news_cr_pub_date'].strftime('%Y-%m-%d %H:%M') if pd.notnull(row['news_cr_pub_date']) else "시간 정보 없음"
                st.caption(f"_{pub_date_str}_")
                st.write(row['news_text_by_agent'])
                
                # '내용 보기' 버튼을 누르면 session_state에 인덱스 저장
                if st.button('기사 원문 보기', key=f"btn_{index}"):
                    st.session_state.selected_article_index = index
                st.markdown("---")

# --- 4컬럼: 원문 ---
with main_cols[3]:
    st.header("기사 원문")
    article_container = st.container(height=600, border=True)

    with article_container:
        # session_state에 저장된 인덱스의 기사 정보를 표시
        if st.session_state.selected_article_index is not None and st.session_state.selected_article_index in df.index:
            article = df.loc[st.session_state.selected_article_index]
            st.markdown(f"**출처:** {article['news_cr_press']}")
            if article['news_link']:
                st.markdown(f"**URL:** [기사 원문 링크]({article['news_link']})")
            st.markdown(f"### {article['news_cr_title']}")
            st.write(article['news_cr_content'])
        else:
            st.info("왼쪽에서 '기사 원문 보기'를 클릭하면 여기에 내용이 표시됩니다.")

# --- 하단: 원본 데이터프레임 표시 ---
st.markdown("---")
st.subheader("업로드된 원본 데이터")
st.dataframe(df)