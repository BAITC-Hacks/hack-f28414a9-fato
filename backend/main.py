from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.pipeline import process_recording
from backend.reports import create_report

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
if not UPLOAD_DIR.is_absolute():
    UPLOAD_DIR = ROOT / UPLOAD_DIR
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "500")) * 1024 * 1024
RESULTS: dict[str, dict[str, Any]] = {}

app = FastAPI(title="AutoProtocol AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "AutoProtocol AI"}


@app.post("/api/process")
def process(file: UploadFile = File(...)) -> dict[str, Any]:
    allowed = {".wav", ".mp3", ".m4a", ".mp4", ".mov", ".webm", ".ogg", ".flac", ".mpeg", ".mpga"}
    suffix = Path(file.filename or "recording").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(415, "Поддерживаются аудио и видео: WAV, MP3, M4A, MP4, MOV, WEBM, OGG, FLAC")
    job_id = uuid.uuid4().hex
    target = UPLOAD_DIR / f"{job_id}{suffix}"
    size = 0
    try:
        with target.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD:
                    raise HTTPException(413, f"Файл превышает лимит {MAX_UPLOAD // (1024 * 1024)} МБ")
                out.write(chunk)
        result = process_recording(target, file.filename or target.name)
        result.update({"id": job_id, "created_at": datetime.now(timezone.utc).isoformat()})
        RESULTS[job_id] = result
        # Keep the original recording only for the duration of processing.
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Не удалось обработать запись: {exc}") from exc
    finally:
        target.unlink(missing_ok=True)
        file.file.close()


@app.get("/api/results/{job_id}/protocol.{fmt}")
def download_protocol(job_id: str, fmt: str) -> FileResponse:
    result = RESULTS.get(job_id)
    if result is None:
        raise HTTPException(404, "Результат не найден. Запустите обработку ещё раз.")
    if fmt not in {"docx", "pdf"}:
        raise HTTPException(404, "Формат не поддерживается")
    path = create_report(result, fmt)
    return FileResponse(path, filename=f"autoprotocol-{job_id[:8]}.{fmt}", media_type=(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if fmt == "docx" else "application/pdf"
    ))
