"""Storage backends for generated diagram images."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path


class ImageStore(ABC):
    """Abstract image storage interface."""

    @abstractmethod
    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        """Store image and return a public URL."""
        ...


class LocalImageStore(ImageStore):
    """Local filesystem storage for development."""

    def __init__(self, base_path: Path, base_url: str):
        self.base_path = base_path
        self.base_url = base_url.rstrip("/")
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        """Store locally and return URL."""
        dir_path = self.base_path / generation_id / section_id
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / filename
        file_path.write_bytes(image_bytes)

        return f"{self.base_url}/{generation_id}/{section_id}/{filename}"


class GCSImageStore(ImageStore):
    """Google Cloud Storage for production."""

    def __init__(self, bucket_name: str):
        from google.cloud import storage

        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        """Store in GCS and return public URL."""
        blob_path = f"{generation_id}/{section_id}/{filename}"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(image_bytes, content_type=f"image/{format}")
        blob.make_public()
        return blob.public_url


def get_image_store() -> ImageStore:
    """Resolve storage backend based on environment."""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        bucket = os.getenv("GCS_BUCKET_NAME", "textbook-diagrams")
        return GCSImageStore(bucket_name=bucket)
    else:
        base_path = Path("data/images")
        base_url = os.getenv("IMAGE_BASE_URL", "http://localhost:8000/images")
        return LocalImageStore(base_path=base_path, base_url=base_url)
