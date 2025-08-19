import json
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
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
    # 경로를 정규화하여 '..' 같은 부분을 처리합니다.
    requested_path = Path(os.path.join(UPLOAD_DIRECTORY, file_path)).resolve()

    # 요청된 경로가 기본 업로드 디렉토리 내에 있는지 확인합니다.
    if not requested_path.is_relative_to(base_path):
        raise HTTPException(status_code=400, detail="안전하지 않은 파일 경로입니다.")
    
    return requested_path

# --- API 엔드포인트 ---

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    프론트엔드에서 전송된 파일들을 받아 서버에 저장합니다.
    파일의 상대 경로를 유지하여 폴더 구조를 그대로 저장합니다.
    """
    for file in files:
        # 파일 경로에 '..' 이 포함되어 있으면 보안 위협으로 간주하고 차단
        if '..' in file.filename:
            raise HTTPException(status_code=400, detail=f"잘못된 파일명입니다: {file.filename}")

        # file.filename에 webkitRelativePath가 포함되어 전달됩니다.
        save_path = Path(UPLOAD_DIRECTORY) / file.filename
        
        # 필요한 하위 디렉토리를 생성합니다.
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일을 저장합니다.
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    return {"message": f"{len(files)}개의 파일이 성공적으로 업로드되었습니다."}


def build_file_tree(directory: str):
    """
    지정된 디렉토리의 파일 구조를 재귀적으로 탐색하여 트리 형태의 객체로 만듭니다.
    """
    tree = []
    base_path = Path(directory)

    for item in sorted(base_path.iterdir()):
        # .DS_Store와 같은 시스템 파일을 무시합니다.
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
            # 폴더가 비어있지 않을 때만 트리에 추가
            if node["children"]:
                tree.append(node)
        elif item.name.endswith('.jsonl'):
            node["type"] = "file"
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
def get_log_content(file_path: str):
    """
    지정된 .jsonl 파일의 내용을 읽어 파싱한 후 리스트로 반환합니다.
    """
    safe_path = get_safe_path(file_path)

    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    logs = []
    try:
        with open(safe_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="로그 파일의 형식이 잘못되었습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일을 읽는 중 오류 발생: {e}")
        
    return logs

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