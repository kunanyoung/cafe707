# ☕ 제주도 카페 상권 분석

소상공인시장진흥공단 상가업소 데이터(`제주카페.xlsx`, 카페 2,912개)를 기반으로 한
제주도 카페 분석 · 한글 지도 시각화 Streamlit 앱입니다.

## 주요 기능
- 🗺️ **한글 지도**: VWorld(국토지리정보원) 일반/위성 지도, OpenStreetMap 선택
- 📍 마커 클러스터 / 히트맵 전환
- 🔎 시군구·행정동 필터, 상호명 검색
- 📊 행정동별 카페 수, 시군구 비중, 층별 분포, 상호명 키워드 분석
- 📋 데이터 표 조회 및 CSV 다운로드

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```
브라우저에서 http://localhost:8501 접속

## 배포 방법

### 1) Streamlit Community Cloud (가장 간단, 무료)
1. GitHub 저장소에 아래 파일을 모두 커밋/푸시
   - `app.py`, `제주카페.xlsx`, `requirements.txt`, `.streamlit/config.toml`
2. https://share.streamlit.io 접속 → **New app**
3. 저장소 / 브랜치 / `app.py` 선택 후 **Deploy**
4. (선택) Advanced settings에서 Python 버전 3.12 지정 권장

> ⚠️ 데이터 파일 `제주카페.xlsx`가 저장소에 포함되어야 앱이 동작합니다.

### 2) Docker (자체 서버 / 클라우드 VM)
```bash
docker build -t jeju-cafe .
docker run -p 8501:8501 jeju-cafe
```
http://localhost:8501 접속

## 파일 구성
| 파일 | 설명 |
|------|------|
| `app.py` | Streamlit 애플리케이션 |
| `제주카페.xlsx` | 원본 데이터 (카페 추출본) |
| `requirements.txt` | Python 의존성 (버전 고정) |
| `.streamlit/config.toml` | 테마·서버 설정 |
| `Dockerfile` / `.dockerignore` | 컨테이너 배포 |
| `.gitignore` | Git 제외 목록 |
