"""
Storage service for handling video uploads to MinIO/S3.
"""
import os
import uuid
from typing import BinaryIO, Optional
from minio import Minio
from minio.error import S3Error
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class StorageService:
    """Service for managing video file storage."""

    def __init__(self):
        """Initialize storage service based on configuration."""
        self.storage_type = os.getenv("STORAGE_TYPE", "minio")  # minio or s3
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "ski-videos")

        if self.storage_type == "minio":
            self._init_minio()
        else:
            self._init_s3()

    def _init_minio(self):
        """Initialize MinIO client."""
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=use_ssl
        )

        # Create bucket if it doesn't exist
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"Error creating bucket: {e}")

    def _init_s3(self):
        """Initialize AWS S3 client."""
        self.client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    def upload_video(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str = "video/mp4"
    ) -> tuple[str, str]:
        """
        Upload video file to storage.

        Args:
            file: File object to upload
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            Tuple of (object_name, storage_url)
        """
        # Generate unique filename
        file_extension = os.path.splitext(filename)[1]
        object_name = f"videos/{uuid.uuid4()}{file_extension}"

        try:
            if self.storage_type == "minio":
                # Get file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Seek back to start

                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    file,
                    file_size,
                    content_type=content_type
                )

                # Generate URL
                storage_url = f"http://{os.getenv('MINIO_ENDPOINT')}/{self.bucket_name}/{object_name}"

            else:  # S3
                self.client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_name,
                    ExtraArgs={'ContentType': content_type}
                )

                storage_url = f"https://{self.bucket_name}.s3.amazonaws.com/{object_name}"

            return object_name, storage_url

        except (S3Error, ClientError) as e:
            raise Exception(f"Failed to upload video: {str(e)}")

    def delete_video(self, object_name: str) -> bool:
        """
        Delete video from storage.

        Args:
            object_name: Name of object to delete

        Returns:
            True if successful
        """
        try:
            if self.storage_type == "minio":
                self.client.remove_object(self.bucket_name, object_name)
            else:
                self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_name
                )
            return True
        except (S3Error, ClientError) as e:
            print(f"Error deleting video: {e}")
            return False

    def get_presigned_url(
        self,
        object_name: str,
        expiry: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access.

        Args:
            object_name: Name of object
            expiry: URL expiry time in seconds (default 1 hour)

        Returns:
            Presigned URL or None if error
        """
        try:
            if self.storage_type == "minio":
                from datetime import timedelta
                url = self.client.presigned_get_object(
                    self.bucket_name,
                    object_name,
                    expires=timedelta(seconds=expiry)
                )
            else:
                url = self.client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_name
                    },
                    ExpiresIn=expiry
                )
            return url
        except (S3Error, ClientError) as e:
            print(f"Error generating presigned URL: {e}")
            return None


# Singleton instance
storage_service = StorageService()
