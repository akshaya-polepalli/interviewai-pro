"""Storage backend selection tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.storage_service import LocalStorageBackend, S3StorageBackend, StorageService


def test_local_storage_roundtrip(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    backend.save(key="a/b.txt", data=b"hello", content_type="text/plain")
    assert backend.exists(key="a/b.txt")
    assert backend.read(key="a/b.txt") == b"hello"
    backend.delete(key="a/b.txt")
    assert not backend.exists(key="a/b.txt")


def test_s3_requires_bucket() -> None:
    settings = Settings(storage_backend="s3", aws_s3_bucket="")
    with pytest.raises(AppError):
        S3StorageBackend(settings)


def test_storage_service_selects_s3() -> None:
    settings = Settings(
        storage_backend="s3",
        aws_s3_bucket="bucket",
        aws_access_key_id="ak",
        aws_secret_access_key="sk",
        aws_s3_region="us-east-1",
    )
    with patch("boto3.client", return_value=MagicMock()):
        svc = StorageService(settings)
        assert isinstance(svc.backend, S3StorageBackend)
