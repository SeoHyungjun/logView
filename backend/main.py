import json
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List

# --- 설정 ---
app = FastAPI()
UPLOAD_DIRECTORY = "log/uploads"

# --- CORS 설정 ---
origins = [
    "http://localhost:5173",  # Vue.js 개발 서버
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 시작 시 업로드 디렉토리 생성 ---
@app.on_event("startup")
def on_startup():
    """애플리케이션 시작 시 업로드 디렉토리가 없으면 생성합니다."""
    os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# --- 보안 헬퍼 함수 ---
def get_safe_path(file_path: str) -> Path:
    """
    사용자로부터 받은 파일 경로를 검증하고 안전한 Path 객체로 반환합니다.
    디렉토리 순회 공격을 방지합니다.
    """
    base_path = Path(UPLOAD_DIRECTORY).resolve()
    requested_path = Path(os.path.join(UPLOAD_DIRECTORY, file_path)).resolve()

    if not requested_path.is_relative_to(base_path):
        raise HTTPException(status_code=400, detail="안전하지 않은 파일 경로입니다.")
    
    return requested_path

# --- API 엔드포인트 ---

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    프론트엔드에서 전송된 파일들을 받아 서버에 저장합니다.
    """
    for file in files:
        if '..' in file.filename:
            raise HTTPException(status_code=400, detail=f"잘못된 파일명입니다: {file.filename}")

        save_path = Path(UPLOAD_DIRECTORY) / file.filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    return {"message": f"{len(files)}개의 파일이 성공적으로 업로드되었습니다."}


def build_file_tree(directory: str):
    """
    지정된 디렉토리의 파일 구조를 재귀적으로 탐색하여 트리 형태의 객체로 만듭니다.
    .jsonl 파일의 경우, 내부를 읽어 각 라인을 대화 세션으로 하는 하위 노드를 생성합니다.
    """
    tree = []
    base_path = Path(directory)

    for item in sorted(base_path.iterdir()):
        if item.name.startswith('.'):
            continue

        rel_path = item.relative_to(UPLOAD_DIRECTORY).as_posix()
        node = {
            "id": rel_path,
            "name": item.name,
            "path": rel_path,
        }
        if item.is_dir():
            node["type"] = "folder"
            node["children"] = build_file_tree(str(item))
            if node["children"]:
                tree.append(node)
        elif item.name.endswith('.jsonl'):
            node["type"] = "file"
            sessions = []
            try:
                with open(item, "r", encoding="utf-8") as f:
                    for i, line in enumerate(f):
                        if line.strip():
                            sessions.append({
                                "id": f"{rel_path}:{i}",
                                "name": f"Conversation {i}",
                                "type": "session",
                                "path": rel_path,
                                "sessionIndex": i
                            })
            except Exception:
                # 파일 읽기 실패 시 세션 목록은 비워둠
                pass
            
            node["children"] = sessions
            tree.append(node)
            
    return tree

@app.get("/api/files")
def get_files():
    """
    업로드된 파일 및 폴더의 전체 트리 구조를 반환합니다.
    """
    if not os.path.exists(UPLOAD_DIRECTORY):
        return []
    return build_file_tree(UPLOAD_DIRECTORY)


@app.get("/api/logs/{file_path:path}")
def get_log_content(file_path: str, session: int = Query(0, description="파일 내 대화 세션의 인덱스")):
    """
    지정된 .jsonl 파일의 특정 세션(라인)을 읽어 대화 목록을 반환합니다.
    """
    safe_path = get_safe_path(file_path)

    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip()]
        
        if session >= len(lines):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

        session_data = json.loads(lines[session])
        
        # 가장 우선적으로 'accumulated_conversations'를 찾습니다.
        if 'accumulated_conversations' in session_data:
            return session_data['accumulated_conversations']
        # 없다면 'conversation'을 찾습니다.
        elif 'conversation' in session_data:
            return session_data['conversation']
        # 둘 다 없다면 전체 데이터를 그대로 반환합니다.
        else:
            return session_data

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="로그 파일의 형식이 잘못되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일을 읽는 중 오류 발생: {e}")

@app.delete("/api/files/{file_path:path}")
def delete_file_or_folder(file_path: str):
    """
    지정된 파일 또는 폴더를 서버에서 삭제합니다.
    """
    safe_path = get_safe_path(file_path)

    try:
        if safe_path.is_file():
            os.remove(safe_path)
        elif safe_path.is_dir():
            shutil.rmtree(safe_path)
        else:
            raise HTTPException(status_code=404, detail="삭제할 파일이나 폴더를 찾을 수 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {e}")

    return {"message": f"'{file_path}'가 성공적으로 삭제되었습니다."}
