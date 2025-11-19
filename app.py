import streamlit as st
import yt_dlp
import os

# --- 클라우드 환경에 맞춘 설정 ---
# 현재 파일이 있는 위치를 기준으로 다운로드 폴더 생성
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "downloads")

# 쿠키 파일은 같은 폴더에 'cookies.txt'로 있다고 가정 (없어도 작동하게 처리)
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

st.set_page_config(page_title="My Cloud Downloader", page_icon="☁️")
st.title("☁️ 서울댁 클라우드 다운로더")
st.info("PC가 꺼져 있어도 작동합니다.")

# 세션 초기화
if 'file_path' not in st.session_state:
    st.session_state.file_path = None
if 'file_name' not in st.session_state:
    st.session_state.file_name = None

url = st.text_input("URL 입력")
filename_input = st.text_input("파일 이름 (확장자 제외)", value="video")

# 1. 클라우드 서버로 다운로드
if st.button("1. 서버로 가져오기"):
    if not url:
        st.warning("URL을 주세요.")
    else:
        status = st.empty()
        status.info("클라우드 서버가 다운로드 중...")
        
        try:
            ydl_opts = {
                'format': 'bv*+ba/b',
                'outtmpl': f'{OUTPUT_DIR}/{filename_input}.%(ext)s',
                'merge_output_format': 'mp4',
                'noplaylist': True,
            }
            
            # 쿠키 파일이 같이 업로드 되어 있다면 사용
            if os.path.exists(COOKIES_FILE):
                ydl_opts['cookiefile'] = COOKIES_FILE
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            final_path = os.path.join(OUTPUT_DIR, f"{filename_input}.mp4")
            
            # 파일 확인 (mkv 등 대비)
            if not os.path.exists(final_path):
                 for f in os.listdir(OUTPUT_DIR):
                    if f.startswith(filename_input):
                        final_path = os.path.join(OUTPUT_DIR, f)
                        break

            if os.path.exists(final_path):
                st.session_state.file_path = final_path
                st.session_state.file_name = os.path.basename(final_path)
                status.success("✅ 완료! 아래 버튼을 누르세요.")
            else:
                status.error("파일을 찾을 수 없습니다.")
                
        except Exception as e:
            status.error(f"에러: {e}")

# 2. 내 폰으로 전송
if st.session_state.file_path and os.path.exists(st.session_state.file_path):
    with open(st.session_state.file_path, "rb") as f:
        st.download_button(
            label="2. 내 폰에 저장하기 📥",
            data=f,
            file_name=st.session_state.file_name,
            mime="video/mp4"
        )