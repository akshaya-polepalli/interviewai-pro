"""
Object storage abstraction.

Local filesystem for development; S3-compatible (AWS / MinIO / R2) when configured.
"""

from __future__ import annotations

import mimetypes
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError, NotFoundError, ValidationAppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def read(self, *, key: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, *, key: str) -> bool:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not str(candidate).startswith(str(self.root)):
            raise ValidationAppError("Invalid storage key")
        return candidate

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("storage_saved", backend="local", key=key, bytes=len(data), content_type=content_type)
        return key

    def read(self, *, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise NotFoundError("File not found in storage")
        return path.read_bytes()

    def delete(self, *, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
            logger.info("storage_deleted", backend="local", key=key)

    def exists(self, *, key: str) -> bool:
        return self._path(key).exists()


class S3StorageBackend(StorageBackend):
    """AWS S3 / MinIO / Cloudflare R2 via boto3."""

    def __init__(self, settings: Settings) -> None:
        if not settings.aws_s3_bucket:
            raise AppError(
                "S3 storage requires AWS_S3_BUCKET (and credentials).",
                code="storage_not_configured",
                status_code=501,
            )
        try:
            import boto3
            from botocore.client import Config
        except ImportError as exc:
            raise AppError(
                "boto3 is not installed. Add boto3 to requirements and rebuild the API image.",
                code="storage_not_configured",
                status_code=501,
            ) from exc

        kwargs: dict = {
            "service_name": "s3",
            "region_name": settings.aws_s3_region or "us-east-1",
        }
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            kwargs["aws_access_key_id"] = settings.aws_access_key_id
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_s3_endpoint_url:
            kwargs["endpoint_url"] = settings.aws_s3_endpoint_url
            kwargs["config"] = Config(s3={"addressing_style": "path"})

        self.bucket = settings.aws_s3_bucket
        self.client = boto3.client(**kwargs)

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type or "application/octet-stream",
        )
        logger.info("storage_saved", backend="s3", key=key, bytes=len(data), content_type=content_type)
        return key

    def read(self, *, key: str) -> bytes:
        try:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            return obj["Body"].read()
        except Exception as exc:
            raise NotFoundError("File not found in storage") from exc

    def delete(self, *, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
        logger.info("storage_deleted", backend="s3", key=key)

    def exists(self, *, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.storage_backend == "s3":
            self.backend: StorageBackend = S3StorageBackend(self.settings)
        else:
            self.backend = LocalStorageBackend(self.settings.storage_local_path)

    def build_resume_key(self, *, user_id: str, filename: str) -> str:
        safe_name = Path(filename).name.replace(" ", "_")
        return f"resumes/{user_id}/{uuid.uuid4().hex}_{safe_name}"

    def build_report_key(self, *, user_id: str, report_id: str, ext: str) -> str:
        safe_ext = ext.lstrip(".")
        return f"reports/{user_id}/{report_id}.{safe_ext}"

    def build_audio_key(self, *, user_id: str, interview_id: str, filename: str) -> str:
        safe_name = Path(filename).name.replace(" ", "_") or "answer.webm"
        return f"audio/{user_id}/{interview_id}/{uuid.uuid4().hex}_{safe_name}"

    def guess_content_type(self, filename: str, declared: str | None) -> str:
        if declared and declared != "application/octet-stream":
            return declared
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"

    def save_bytes(self, *, key: str, data: bytes, content_type: str) -> str:
        return self.backend.save(key=key, data=data, content_type=content_type)

    def read_bytes(self, *, key: str) -> bytes:
        return self.backend.read(key=key)

    def delete(self, *, key: str) -> None:
        self.backend.delete(key=key)
