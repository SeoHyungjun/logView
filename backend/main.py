import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 개발 중에는 모든 출처의 요청을 허용합니다.
origins = [
    "http://localhost:5173",  # Vue.js 개발 서버의 기본 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/logs")
def get_logs():
    """
    log.jsonl 파일을 읽어 각 줄을 JSON 객체로 변환하고 리스트로 반환합니다.
    """
    logs = []
    try:
        # backend 디렉토리 안에 있는 log.jsonl 파일을 읽습니다.
        with open("log.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                logs.append(json.loads(line))
    except FileNotFoundError:
        return {"error": "log.jsonl 파일을 찾을 수 없습니다."}
    except json.JSONDecodeError:
        return {"error": "로그 파일의 형식이 잘못되었습니다."}
    return logs
