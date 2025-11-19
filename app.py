import streamlit as st
import subprocess
import os
import tempfile
import base64
from pathlib import Path
import time

# --- 환경 설정 ---
# Streamlit Secrets에서 쿠키 파일을 가져와 사용할 임시 파일 경로를 설정합니다.
# Secrets에 "cookies_data"가 없으면 None으로 설정됩니다.
COOKIES_FILE = None 
if 'cookies_data' in st.secrets and st.secrets["cookies_data"].strip():
    try:
        # Secrets 내용을 임시 파일로 저장합니다. 
        # Streamlit Cloud에서는 임시 폴더를 사용해야 합니다.
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, "yt_cookies.txt")
        
        # 다중 줄 문자열을 임시 파일에 그대로 씁니다.
        with open(temp_file_path, "w", encoding="utf-8") as f:
            f.write(st.secrets["cookies_data"])
        
        COOKIES_FILE = temp_file_path
        
    except Exception as e:
        st.error(f"⚠️ 쿠키 파일 생성 오류: {e}")
        COOKIES_FILE = None


def get_video_filename(url, cookies_path):
    """yt-dlp를 사용하여 다운로드될 파일명을 미리 예측합니다."""
    # --print "filename" 옵션을 사용하여 최종 파일명을 예측합니다.
    cmd = [
        "yt-dlp",
        "--restrict-filenames",
        "--print", "filename",
        "-o", "%(title)s.%(ext)s",
        url
    ]
    if cookies_path:
        cmd.extend(["--cookies", cookies_path])
        
    try:
        # 파일명을 예측할 때는 video-quality를 지정하지 않습니다.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
        # 예측된 파일명에서 확장자를 제외하고 순수한 제목만 반환합니다.
        # yt-dlp는 기본적으로 가장 좋은 확장자를 선택하므로, .mp4 등으로 고정하지 않습니다.
        return result.stdout.strip().rsplit('.', 1)[0]
    except Exception as e:
        st.error(f"❌ 파일명 예측 실패 (유효한 URL인지 확인하세요): {e}")
        return None

def download_video(url, cookies_path, output_filename_base):
    """
    yt-dlp를 사용하여 동영상을 다운로드하고 mp4로 합칩니다.
    쿠키와 파일명 제한 옵션을 포함하여 403 에러를 방지합니다.
    """
    # 임시 출력 파일 경로 설정 (yt-dlp가 임시 파일을 여기에 저장합니다)
    temp_dir = tempfile.gettempdir()
    temp_output_path = os.path.join(temp_dir, output_filename_base)
    
    # yt-dlp 명령어 정의 (가장 안정적인 옵션)
    cmd = [
        "yt-dlp",
        # 최적의 화질 및 오디오 포맷 선택 (-f bestvideo+bestaudio/best)
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        # 다운로드 후 비디오/오디오를 mp4로 합칩니다 (FFmpeg 필요)
        "--recode-video", "mp4",
        # 파일명을 안전하게 제한합니다.
        "--restrict-filenames", 
        # 임시 파일을 저장할 경로와 최종 파일명 지정
        "-o", f"{temp_output_path}.%(ext)s", 
        url
    ]
    
    # 쿠키 파일 경로가 있다면 명령어에 추가
    if cookies_path:
        cmd.extend(["--cookies", cookies_path])
        st.info(f"✅ 로그인 쿠키를 사용하여 다운로드 시도 중...")
    else:
        st.warning("⚠️ Secrets에 쿠키 정보가 없어 로그인 없이 다운로드합니다.")

    # 다운로드 시작
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        
        # Streamlit에 로그 출력 (다운로드 진행 상황)
        log_container = st.empty()
        log_output = []
        for line in iter(process.stdout.readline, ''):
            log_output.append(line)
            # 마지막 10줄만 보여주어 화면이 넘치는 것을 방지
            log_container.code("".join(log_output[-10:]), language='log')

        process.wait()

        if process.returncode != 0:
            st.error("❌ 다운로드 실패! 로그를 확인하세요.")
            st.code("".join(log_output), language='log')
            return None

        # yt-dlp는 recode 후 확장자를 .mp4로 최종 출력합니다.
        final_file_path = f"{temp_output_path}.mp4"
        
        if os.path.exists(final_file_path):
            return final_file_path
        else:
            st.error(f"❌ 다운로드는 완료되었으나 최종 파일({final_file_path})을 찾을 수 없습니다.")
            return None
            
    except Exception as e:
        st.error(f"❌ 치명적인 다운로드 오류가 발생했습니다: {e}")
        return None

# --- Streamlit UI 구성 ---
st.set_page_config(page_title="유튜브 쇼츠 다운로더 (Streamlit & yt-dlp)", layout="centered")
st.title("🎬 유튜브 쇼츠/비디오 다운로더")
st.caption("Streamlit Cloud, yt-dlp, FFmpeg 사용. 403 에러 방지를 위해 Secrets에 유효한 YouTube 쿠키 필요.")

if COOKIES_FILE:
    st.success("Secrets에서 쿠키 파일을 성공적으로 불러왔습니다.")
else:
    st.error("Secrets에 'cookies_data'가 설정되지 않았습니다. 비공개 영상 다운로드는 불가능합니다.")

url_input = st.text_input("1. 유튜브 쇼츠/비디오 URL을 여기에 붙여넣으세요.", placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ")

if 'downloaded_path' not in st.session_state:
    st.session_state.downloaded_path = None

if st.button("서버로 가져오기 🚀", use_container_width=True, type="primary"):
    if url_input:
        st.session_state.downloaded_path = None # 상태 초기화
        with st.spinner("⏳ 동영상 정보 확인 및 다운로드/합치기(FFmpeg) 중... (10~30초 소요)"):
            
            # 1. 최종 파일명 예측
            base_filename = get_video_filename(url_input, COOKIES_FILE)
            
            if base_filename:
                # 2. 다운로드 실행
                st.session_state.downloaded_path = download_video(url_input, COOKIES_FILE, base_filename)
            
            if st.session_state.downloaded_path:
                st.success("✅ 다운로드 및 변환 완료!")
            else:
                st.error("❌ 다운로드에 실패했습니다. 위의 로그를 확인하거나 쿠키를 갱신하세요.")
    else:
        st.warning("URL을 입력해 주세요.")

# --- 다운로드 링크 생성 ---
if st.session_state.downloaded_path:
    final_path = st.session_state.downloaded_path
    
    try:
        # 파일을 읽어 base64로 인코딩하여 다운로드 링크를 만듭니다.
        with open(final_path, "rb") as f:
            video_bytes = f.read()
        
        b64 = base64.b64encode(video_bytes).decode()
        
        # 파일명을 깨끗하게 정리하여 다운로드 파일명으로 사용
        clean_filename = Path(final_path).name.replace(tempfile.gettempdir(), "").strip(os.sep)

        st.markdown(f"""
            <a href="data:video/mp4;base64,{b64}" download="{clean_filename}">
                <button style="
                    background-color: #4CAF50; 
                    color: white; 
                    padding: 10px 20px; 
                    border: none; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    width: 100%;
                    font-size: 1.1em;">
                    2. 내 폰에 저장하기 📥 ({clean_filename})
                </button>
            </a>
            """, unsafe_allow_html=True)

        st.caption("다운로드가 완료된 후에는 파일을 삭제하여 서버 공간을 절약합니다.")

    except Exception as e:
        st.error(f"❌ 다운로드 링크 생성 중 오류: {e}")
        
    finally:
        # 다운로드 후 임시 파일 삭제 (서버 공간 관리)
        if os.path.exists(final_path):
            os.remove(final_path)
            # st.info("임시 파일이 삭제되었습니다.")
        # yt-dlp가 남긴 임시 파일도 정리
        for ext in ['.part', '.temp', '.ytdl']:
            temp_part_file = final_path.replace('.mp4', ext)
            if os.path.exists(temp_part_file):
                os.remove(temp_part_file)
