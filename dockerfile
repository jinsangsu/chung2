# ⚙️ 빌드 스테이지: 의존성 설치 및 가상환경 준비
# Python 3.11-slim 이미지를 기반으로 합니다. (더 작은 이미지 크기를 위해)
FROM python:3.11-slim AS builder

# Python 버퍼링 비활성화 및 바이트코드 생성을 막아 이미지 크기 최적화
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# /app 디렉토리를 작업 디렉토리로 설정
WORKDIR /app

# 가상환경 설정 및 의존성 설치
# /opt/venv 경로에 가상환경을 생성합니다.
RUN python -m venv /opt/venv
# PATH 환경 변수에 가상환경의 bin 디렉토리를 추가하여 가상환경 내부의 Python 실행
ENV PATH="/opt/venv/bin:$PATH"

# requirements.txt 파일을 현재 작업 디렉토리( /app )로 복사
COPY requirements.txt ./
# requirements.txt에 명시된 모든 Python 패키지를 설치합니다.
# --no-cache-dir 옵션은 패키지 캐시를 저장하지 않아 이미지 크기를 줄입니다.
RUN pip install --no-cache-dir -r requirements.txt

# ⚙️ 실제 실행 이미지: 더 가볍고 최종 사용자에게 배포될 이미지
# 동일한 Python 3.11-slim 이미지를 기반으로 시작합니다.
FROM python:3.11-slim

# /app 디렉토리를 작업 디렉토리로 설정
WORKDIR /app

# 빌드 스테이지에서 생성된 가상환경을 최종 이미지로 복사
COPY --from=builder /opt/venv /opt/venv
# PATH 환경 변수를 다시 설정하여 최종 이미지에서도 가상환경을 사용하도록 합니다.
ENV PATH="/opt/venv/bin:$PATH"

# 애플리케이션 코드 및 필요한 파일을 현재 작업 디렉토리( /app )로 복사합니다.
# 이 명령이 프로젝트 루트에 있는 main.py, app.py, fly.toml, aesoonkey.json 등을 모두 복사합니다.
COPY . .

# ✅ FastAPI 앱 실행 명령어
# 앱이 시작될 때 실행될 명령어입니다. Uvicorn을 사용하여 main.py의 app 인스턴스를 실행합니다.
# --host 0.0.0.0 은 모든 네트워크 인터페이스에서 접근 가능하게 합니다.
# --port 8000 은 앱이 8000번 포트에서 요청을 수신하도록 합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# 컨테이너의 8000번 포트를 외부에 노출합니다.
EXPOSE 8000