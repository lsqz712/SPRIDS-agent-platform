"""
对象存储文件访问 API
"""
from minio.error import S3Error
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.storage.minio_client import minio_client

router = APIRouter(prefix="/api/storage", tags=["存储"])


@router.get("/{object_path:path}")
async def get_storage_object(object_path: str):
    try:
        response = minio_client.get_object_stream(object_path)
    except S3Error as exc:
        raise HTTPException(status_code=404, detail="文件不存在") from exc

    media_type = response.headers.get("Content-Type", "application/octet-stream")

    def stream():
        try:
            for chunk in response.stream(32 * 1024):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(stream(), media_type=media_type)
