# Log Viewer

Log Viewer는 JSONL 형식의 로그 파일을 시각적으로 쉽게 확인하고 분석할 수 있도록 돕는 웹 애플리케이션입니다. 백엔드는 Python의 FastAPI로, 프론트엔드는 Vue.js와 Vite로 개발되었습니다.

## 🚀 시작하기

이 프로젝트를 로컬 환경에서 실행하기 위한 설정 및 실행 방법입니다.

### 📋 전제 조건

프로젝트를 실행하기 전에 다음 소프트웨어가 시스템에 설치되어 있어야 합니다:

*   **Python 3.8+**: 백엔드 실행을 위해 필요합니다.
    *   [Python 공식 웹사이트](https://www.python.org/downloads/)
*   **Node.js 16+ & npm**: 프론트엔드 실행을 위해 필요합니다.
    *   [Node.js 공식 웹사이트](https://nodejs.org/en/download/)

### 📦 설치 및 실행

#### 1. 프로젝트 클론

```bash
git clone https://github.com/SeoHyungjun/logView.git # 실제 레포지토리 URL로 대체해주세요
cd logView
```

#### 2. 백엔드 설정 및 실행

1.  **가상 환경 설정 및 의존성 설치**

    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate # macOS/Linux
    # venv\Scripts\activate # Windows
    pip install "fastapi[all]" python-multipart
    ```

2.  **백엔드 서버 실행**

    ```bash
    uvicorn main:app --reload --host 0.0.0.0
    ```

    서버는 기본적으로 `http://127.0.0.1:8000`에서 실행됩니다.

#### 3. 프론트엔드 설정 및 실행

1.  **의존성 설치**

    ```bash
    cd ../frontend
    npm install
    ```

2.  **프론트엔드 애플리케이션 실행**

    ```bash
    npm run dev -- --host 0.0.0.0
    ```

    프론트엔드 애플리케이션은 기본적으로 `http://localhost:5173`에서 실행됩니다. 백엔드 서버가 실행 중이어야 정상적으로 로그 데이터를 가져올 수 있습니다.

## 💡 주요 기능

*   **JSONL 로그 파일 뷰어**: 드래그 앤 드롭 또는 파일 선택을 통해 로컬의 `.jsonl` 파일을 쉽게 로드하고 내용을 확인할 수 있습니다.
*   **코드 하이라이팅**: 로그 내용에 포함된 다양한 언어의 코드 블록(` ``` `)에 대해 자동으로 구문 하이라이팅을 적용하여 가독성을 높입니다.
*   **파일 트리 탐색**: 로드된 파일 및 폴더 구조를 트리 형태로 표시하여 여러 로그 파일을 쉽게 탐색하고 전환할 수 있습니다.
*   **편리한 UI/UX**: 키보드 방향키를 이용한 대화 탐색, 접고 펼 수 있는 사이드 패널 등 사용자 편의 기능을 제공합니다.

## 📁 데이터 구조

본 애플리케이션은 `.jsonl` 파일을 사용하며, 각 라인은 하나의 대화 세션을 나타내는 JSON 객체입니다. 각 JSON 객체는 다음과 같은 구조를 가집니다.

*   `index` (number): 대화의 고유 식별자입니다.
*   `category` (string): 대화의 주 카테고리입니다.
*   `sub_category` (string): 대화의 서브 카테고리입니다.
*   `language` (string): 대화에 사용된 언어입니다. (예: "KO")
*   `turns` (number): 대화가 오고간 횟수입니다.
*   `criteria` (Array<string>): 응답을 평가하는 기준 목록입니다.
*   `conversation` (Array<Object>): 사용자가 입력한 모든 질문의 목록입니다.
    *   `role` (string): "user"
    *   `content` (string): 사용자 질문 내용
*   `response` (Array<string>): 어시스턴트가 답변한 모든 내용의 목록입니다.
*   `accumulated_conversations` (Array<Object>): 전체 대화 내용의 목록입니다.
    *   `role` (string): "user" 또는 "assistant"
    *   `content` (string): 대화 내용

### 예시 데이터

```json
{"index": 5, "category": "Programming", "language": "KO", "sub_category": "Multi-language", "turns": 4, "criteria": ["Code Quality", "Accuracy"], "conversation": [{"role": "user", "content": "파이썬 코드 예시를 보여줘."}, ...], "expected_results": ["...\n```python\n...\n```", "..."], "accumulated_conversations": [{"role": "user", "content": "파이썬 코드 예시를 보여줘."}, {"role": "assistant", "content": "...\n```python\n...\n```"}, ...], "response": ["...\n```python\n...\n```", "..."]}
```

## 📁 프로젝트 구조

```
logView/
├── backend/             # FastAPI 백엔드 애플리케이션
│   ├── main.py          # 백엔드 메인 파일
├── frontend/            # Vue.js 프론트엔드 애플리케이션
│   ├── src/             # Vue.js 소스 코드
│   │   ├── App.vue      # 메인 Vue 컴포넌트
│   │   └── main.ts      # Vue 애플리케이션 엔트리 포인트
│   ├── package.json     # Node.js/npm 의존성 및 스크립트
│   └── vite.config.ts   # Vite 설정 파일
├── log/                 # 예시 로그 파일 디렉토리
└── README.md            # 프로젝트 설명 파일
```