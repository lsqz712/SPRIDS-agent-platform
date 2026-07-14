"""
MinIO 对象存储客户端封装
用于存储检测图像、训练模型等文件
"""
import io
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.config.settings import settings


class MinIOClient:
    """MinIO 客户端封装"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket_name = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self):
        """确保存储桶存在，不存在则创建"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            print(f"MinIO bucket 初始化警告: {e}")

    def upload_file(self, object_name: str, file_path: str) -> str:
        """上传本地文件到 MinIO，返回预签名 URL"""
        self.client.fput_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            file_path=file_path,
        )
        return self.get_presigned_url(object_name)

    def upload_bytes(
        self, object_name: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        """上传字节数据到 MinIO，返回预签名 URL"""
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return self.get_presigned_url(object_name)

    def get_presigned_url(self, object_name: str) -> str:
        """获取对象的预签名访问 URL（有效期 7 天）"""
        return self.client.presigned_get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            expires=timedelta(days=7),
        )

    def get_object_stream(self, object_name: str):
        """获取 MinIO 对象流（调用方负责 close/release）"""
        return self.client.get_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
        )

    def build_public_url(self, object_name: str) -> str:
        """构建通过后端代理访问的持久 URL"""
        return f"/api/storage/{object_name}"

    def delete_file(self, object_name: str):
        """删除 MinIO 中的文件"""
        self.client.remove_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
        )


minio_client = MinIOClient()