"""Storage for legacy single-photo uploads: local folder (default), MinIO or S3.

The client libraries for MinIO/S3 are imported only when that backend is
selected, and nothing connects at import time, so the API starts with no
services running.
"""
import os
import uuid
from typing import BinaryIO, Optional

from config import DATA_DIR, STORAGE_TYPE


class StorageService:
    def __init__(self):
        self.storage_type = STORAGE_TYPE
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "ski-videos")
        self.local_root = os.path.join(DATA_DIR, "uploads")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if self.storage_type == "minio":
                from minio import Minio
                self._client = Minio(
                    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
                    access_key=os.environ["MINIO_ACCESS_KEY"],
                    secret_key=os.environ["MINIO_SECRET_KEY"],
                    secure=os.getenv("MINIO_USE_SSL", "false").lower() == "true",
                )
                if not self._client.bucket_exists(self.bucket_name):
                    self._client.make_bucket(self.bucket_name)
            elif self.storage_type == "s3":
                import boto3
                self._client = boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))
        return self._client

    def upload_video(self, file: BinaryIO, filename: str, content_type: str = "video/mp4") -> tuple[str, str]:
        """Store a file. Returns (object_name, storage_url)."""
        object_name = f"videos/{uuid.uuid4()}{os.path.splitext(filename)[1].lower()}"
        file.seek(0)
        if self.storage_type == "local":
            path = os.path.join(self.local_root, object_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as out:
                while chunk := file.read(1024 * 1024):
                    out.write(chunk)
            return object_name, f"local://{object_name}"
        if self.storage_type == "minio":
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            self.client.put_object(self.bucket_name, object_name, file, size, content_type=content_type)
            return object_name, f"http://{os.getenv('MINIO_ENDPOINT', 'localhost:9000')}/{self.bucket_name}/{object_name}"
        self.client.upload_fileobj(file, self.bucket_name, object_name, ExtraArgs={"ContentType": content_type})
        return object_name, f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"

    def read(self, object_name: str) -> Optional[bytes]:
        """Fetch a stored object's bytes (None when missing)."""
        try:
            if self.storage_type == "local":
                with open(os.path.join(self.local_root, object_name), "rb") as fh:
                    return fh.read()
            if self.storage_type == "minio":
                resp = self.client.get_object(self.bucket_name, object_name)
                try:
                    return resp.read()
                finally:
                    resp.close()
                    resp.release_conn()
            return self.client.get_object(Bucket=self.bucket_name, Key=object_name)["Body"].read()
        except Exception as e:  # noqa: BLE001 - any backend error means "not available"
            print(f"Storage read failed for {object_name}: {e}")
            return None

    def delete_video(self, object_name: str) -> bool:
        try:
            if self.storage_type == "local":
                path = os.path.join(self.local_root, object_name)
                if os.path.exists(path):
                    os.remove(path)
            elif self.storage_type == "minio":
                self.client.remove_object(self.bucket_name, object_name)
            else:
                self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except Exception as e:  # noqa: BLE001
            print(f"Error deleting {object_name}: {e}")
            return False


storage_service = StorageService()
