# storage_manager\storage_backend.py

import os
import json
from pathlib import Path
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from src.common.logging.logger import logger  # optional for proper logging

class StorageBackend:
    """Abstract base class for storage backends."""
    def save_json(self, key: str, data: dict):
        raise NotImplementedError

    def load_json(self, key: str) -> dict:
        raise NotImplementedError

    def save_file(self, src_path: Path, dest_key: str):
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """Local filesystem storage."""
    def __init__(self, base_dir="sessions"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def _full_path(self, key: str) -> Path:
        return self.base / key

    def save_json(self, key: str, data: dict):
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_json(self, key: str) -> dict:
        path = self._full_path(key)
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def save_file(self, src_path: Path, dest_key: str):
        dest = self._full_path(dest_key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src_path.read_bytes())


class S3Storage(StorageBackend):
    """Amazon S3 storage."""
    def __init__(self, bucket_name: str, base_prefix: str = "sessions"):
        self.bucket = bucket_name
        self.prefix = base_prefix.strip("/")
        self.s3 = boto3.client("s3", region_name=os.getenv("AWS_REGION"))

    def _s3_key(self, key: str) -> str:
        return f"{self.prefix}/{key}".replace("\\", "/")

    def save_json(self, key: str, data: dict):
        try:
            body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            self.s3.put_object(Bucket=self.bucket, Key=self._s3_key(key), Body=body)
        except (BotoCoreError, ClientError) as e:
            logger.error(f"[S3] Failed to save {key}: {e}")

    def load_json(self, key: str) -> dict:
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=self._s3_key(key))
            return json.loads(obj["Body"].read())
        except self.s3.exceptions.NoSuchKey:
            return {}
        except (BotoCoreError, ClientError) as e:
            logger.error(f"[S3] Failed to load {key}: {e}")
            return {}

    def save_file(self, src_path: Path, dest_key: str):
        try:
            self.s3.upload_file(str(src_path), self.bucket, self._s3_key(dest_key))
        except (BotoCoreError, ClientError) as e:
            logger.error(f"[S3] Failed to upload {dest_key}: {e}")


class CompositeStorage(StorageBackend):
    """Writes to both primary and fallback storage, reads from primary first."""
    def __init__(self, primary: StorageBackend, fallback: StorageBackend):
        self.primary = primary
        self.fallback = fallback

    def save_json(self, key: str, data: dict):
        self.fallback.save_json(key, data)
        self.primary.save_json(key, data)

    def load_json(self, key: str) -> dict:
        data = self.primary.load_json(key)
        if data:
            return data
        return self.fallback.load_json(key)

    def save_file(self, src_path: Path, dest_key: str):
        self.fallback.save_file(src_path, dest_key)
        self.primary.save_file(src_path, dest_key)
