# Log Viewer

Log Viewer는 JSONL 형식의 로그 파일을 시각적으로 쉽게 확인하고 분석할 수 있도록 돕는 웹 애플리케이션입니다. 백엔드는 Python의 FastAPI로, 프론트엔드는 Vue.js와 Vite로 개발되었습니다.

## 🚀 시작하기

이 프로젝트를 로컬 환경에서 실행하기 위한 설정 및 실행 방법입니다.

### 📋 전제 조건

프로젝트를 실행하기 전에 다음 소프트웨어가 시스템에 설치되어 있어야 합니다:

*   **Python 3.8+**: 백엔드 실행을 위해 필요합니다.
    *   [Python 공식 웹사이트](https://www.python.org/downloads/)
*   **Node.js 14+ & npm (또는 yarn)**: 프론트엔드 실행을 위해 필요합니다.
    *   [Node.js 공식 웹사이트](https://nodejs.org/en/download/)

### 📦 설치 및 실행

#### 1. 프로젝트 클론

```bash
git clone https://github.com/SeoHyungjun/logView.git # 실제 레포지토리 URL로 대체해주세요
cd logView
```

#### 2. 백엔드 설정 및 실행

백엔드는 Python FastAPI를 사용합니다. `*.jsonl` 파일을 읽어 로그 데이터를 제공합니다.

1.  **가상 환경 설정 및 의존성 설치**

    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate # macOS/Linux
    # venv\Scripts\activate # Windows
    pip install -r requirements.txt # requirements.txt 파일이 없으면 직접 설치
    # 필요한 패키지: fastapi, uvicorn, pydantic, python-multipart, python-dotenv 등
    # 현재 main.py에 명시된 패키지는 fastapi, uvicorn, starlette, pydantic 입니다.
    pip install "fastapi[all]"
    ```

2.  **로그 파일 준비**

    `.jsonl` 형식의 파일을 읽습니다.

    예시 `log.jsonl` 내용:
    ```jsonl
    {"role": "user", "content": "Hello, world!"}
    {"role": "assistant", "content": "```python\nprint(\"Hello from Python!\")\n```"}
    ```

3.  **백엔드 서버 실행**

    ```bash
    uvicorn main:app --reload
    ```

    서버는 기본적으로 `http://127.0.0.1:8000`에서 실행됩니다.

#### 3. 프론트엔드 설정 및 실행

프론트엔드는 Vue.js와 Vite를 사용합니다.

1.  **의존성 설치**

    ```bash
    cd ../frontend
    npm install # 또는 yarn install
    ```

2.  **프론트엔드 애플리케이션 실행**

    ```bash
    npm run dev # 또는 yarn dev
    ```

    프론트엔드 애플리케이션은 기본적으로 `http://localhost:5173`에서 실행됩니다. 백엔드 서버가 실행 중이어야 정상적으로 로그 데이터를 가져올 수 있습니다.

## 💡 주요 기능

*   **JSONL 로그 파일 뷰어**: JSONL 형식의 로그 파일을 드래그 앤 드롭하거나 파일 선택을 통해 쉽게 로드하고 내용을 확인할 수 있습니다.
*   **코드 하이라이팅**: 로그 내용에 포함된 코드 블록(` ``` `)에 대해 자동으로 구문 하이라이팅을 적용하여 가독성을 높입니다.
*   **파일 탐색**: 로드된 파일 목록을 트리 형태로 표시하여 여러 로그 파일을 쉽게 탐색하고 전환할 수 있습니다.

## 📁 프로젝트 구조

```
logView/
├── backend/             # FastAPI 백엔드 애플리케이션
│   ├── main.py          # 백엔드 메인 파일
│   └── requirements.txt # Python 의존성 (필요시 생성)
├── frontend/            # Vue.js 프론트엔드 애플리케이션
│   ├── src/             # Vue.js 소스 코드
│   │   ├── App.vue      # 메인 Vue 컴포넌트
│   │   └── main.ts      # Vue 애플리케이션 엔트리 포인트
│   ├── package.json     # Node.js/npm 의존성 및 스크립트
│   └── vite.config.ts   # Vite 설정 파일
├── log/                 # 예시 로그 파일 디렉토리 (선택 사항)
└── README.md            # 프로젝트 설명 파일
```