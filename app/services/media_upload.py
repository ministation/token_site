import os
import datetime
import shutil
from fastapi import UploadFile, HTTPException
from app.config import UPLOAD_DIR

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".webm", ".mov"}
IMAGE_MAX_BYTES = 8 * 1024 * 1024
VIDEO_MAX_BYTES = 50 * 1024 * 1024
CHAT_IMAGE_MAX_BYTES = 5 * 1024 * 1024


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload(
    file: UploadFile,
    owner_id: str,
    *,
    kind: str = "image",
    prefix: str = "",
) -> str:
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Файл не выбран")

    ext = os.path.splitext(file.filename)[1].lower()
    if kind == "video":
        if ext not in VIDEO_EXTS:
            raise HTTPException(status_code=400, detail="Видео: только MP4, WebM или MOV")
        max_bytes = VIDEO_MAX_BYTES
    else:
        if ext not in IMAGE_EXTS:
            raise HTTPException(status_code=400, detail="Изображение: JPG, PNG, GIF или WebP")
        max_bytes = CHAT_IMAGE_MAX_BYTES if prefix == "chat" else IMAGE_MAX_BYTES

    _ensure_upload_dir()
    tag = prefix or kind
    filename = f"{tag}_{owner_id}_{int(datetime.datetime.now().timestamp())}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    size = 0
    with open(filepath, "wb") as buffer:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                buffer.close()
                os.remove(filepath)
                limit_mb = max_bytes // (1024 * 1024)
                raise HTTPException(status_code=400, detail=f"Файл слишком большой (макс. {limit_mb} МБ)")
            buffer.write(chunk)

    return f"/static/uploads/{filename}"
