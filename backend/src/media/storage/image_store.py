from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from core.config import settings
from core.storage.gcs_image_store import (
    PRODUCTION_LIKE_ENVS,
    GCSImageStore as CoreGCSImageStore,
)


logger = logging.getLogger(__name__)

_DEFAULT_LOCAL_IMAGE_BASE_URL = "http://localhost:8000/images"
_KNOWN_PROVIDER_API_HOSTS = frozenset({"api.x.ai", "api.openai.com"})


def _provider_base_urls() -> tuple[str, ...]:
    """Return configured provider endpoints, kept separate from storage URLs."""

    values: list[str] = []
    if os.getenv("IMAGE_PROVIDER"):
        direct_url = os.getenv("IMAGE_BASE_URL")
        if direct_url:
            values.append(direct_url)
    if os.getenv("PIPELINE_IMAGE_PROVIDER"):
        pipeline_url = os.getenv("PIPELINE_IMAGE_BASE_URL")
        if pipeline_url:
            values.append(pipeline_url)
    return tuple(values)


def _is_provider_endpoint(url: str) -> bool:
    candidate = urlsplit(url.strip())
    if candidate.hostname in _KNOWN_PROVIDER_API_HOSTS:
        return True

    for configured in _provider_base_urls():
        provider = urlsplit(configured.strip())
        if (
            candidate.scheme.lower() == provider.scheme.lower()
            and candidate.netloc.lower() == provider.netloc.lower()
            and candidate.path.rstrip("/") == provider.path.rstrip("/")
        ):
            return True
    return False


def _validate_storage_base_url(url: str) -> str:
    normalized = url.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Image storage base URL must be an absolute HTTP(S) URL")
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Image storage base URL must use HTTP(S)")
    if _is_provider_endpoint(normalized):
        raise ValueError(
            "Image storage base URL must not point at an image provider endpoint; "
            "set IMAGE_STORAGE_BASE_URL to the served storage route"
        )
    return normalized


def _resolve_local_storage_base_url() -> str:
    explicit = settings.image_storage_base_url
    if explicit and explicit.strip():
        return _validate_storage_base_url(explicit)

    legacy = settings.image_base_url or _DEFAULT_LOCAL_IMAGE_BASE_URL
    # In direct-provider mode IMAGE_BASE_URL belongs to the provider.  If an
    # older config also exposes it as the storage URL, fall back to the route
    # served by this app instead of returning an API endpoint to the Builder.
    if _is_provider_endpoint(legacy):
        logger.warning(
            "Ignoring legacy IMAGE_BASE_URL for local image storage because it "
            "is a provider endpoint; use IMAGE_STORAGE_BASE_URL for storage"
        )
        return _DEFAULT_LOCAL_IMAGE_BASE_URL
    return _validate_storage_base_url(legacy)


class ImageStore(ABC):
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
        ...

    async def store_image_key(
        self,
        *,
        key: str,
        image_bytes: bytes,
        content_type: str = "image/png",
    ) -> str:
        ...

    async def image_exists(self, *, key: str) -> bool:
        ...

    async def copy_image(self, *, source_key: str, destination_key: str) -> str | None:
        ...

    @abstractmethod
    async def probe_write_access(self) -> tuple[bool, str]:
        ...

    @abstractmethod
    def describe_target(self) -> str:
        ...


class LocalImageStore(ImageStore):
    def __init__(self, base_path: Path, base_url: str):
        self.base_path = base_path
        self.base_url = _validate_storage_base_url(base_url)
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
        _ = format
        dir_path = self.base_path / generation_id / section_id
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / filename
        file_path.write_bytes(image_bytes)
        return f"{self.base_url}/{generation_id}/{section_id}/{filename}"

    async def store_image_key(
        self,
        *,
        key: str,
        image_bytes: bytes,
        content_type: str = "image/png",
    ) -> str:
        _ = content_type
        clean_key = key.strip("/")
        file_path = self.base_path / clean_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(image_bytes)
        url_key = clean_key.replace("\\", "/")
        return f"{self.base_url}/{url_key}"

    async def image_exists(self, *, key: str) -> bool:
        return (self.base_path / key.strip("/")).exists()

    async def copy_image(self, *, source_key: str, destination_key: str) -> str | None:
        source = self.base_path / source_key.strip("/")
        if not source.exists():
            return None
        clean_destination = destination_key.strip("/")
        destination = self.base_path / clean_destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        url_key = clean_destination.replace("\\", "/")
        return f"{self.base_url}/{url_key}"

    async def probe_write_access(self) -> tuple[bool, str]:
        probe_dir = self.base_path / "_health"
        probe_file = probe_dir / f".probe-{uuid4().hex}"

        try:
            probe_dir.mkdir(parents=True, exist_ok=True)
            probe_file.write_bytes(b"ok")
            probe_file.unlink(missing_ok=True)
        except Exception as exc:
            return False, f"local write failed at {self.base_path}: {type(exc).__name__}: {exc}"

        return True, f"local path writable at {self.base_path}"

    def describe_target(self) -> str:
        return f"local:{self.base_path}"


class GCSImageStore(ImageStore):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._core_store = CoreGCSImageStore(bucket_name=bucket_name)
        self.base_url = self._core_store._base_url.rstrip("/")
        self.credential_source = self._core_store.credential_source
        self.credentials_resolved = self._core_store.credentials_resolved
        self.client = self._core_store.client

    async def store_image(
        self,
        image_bytes: bytes,
        *,
        generation_id: str,
        section_id: str,
        filename: str,
        format: str = "png",
    ) -> str:
        blob_path = f"{generation_id}/{section_id}/{filename}"
        content_type = f"image/{format}"

        logger.info(
            "v3 visual gcs upload start",
            extra={
                "node_name": "visual_executor",
                "generation_id": generation_id,
                "bucket_name": self.bucket_name,
                "blob_path": blob_path,
                "credential_source": self.credential_source,
                "credentials_resolved": self.credentials_resolved,
                "auth_client": type(self.client).__name__ if self.client is not None else None,
                "content_type": content_type,
                "byte_count": len(image_bytes),
            },
        )
        try:
            final_url = await self._core_store.upload_with_key(
                key=blob_path,
                image_bytes=image_bytes,
                content_type=content_type,
            )
            if not final_url:
                raise RuntimeError("GCS upload returned no URL")
            logger.info(
                "v3 visual gcs upload complete",
                extra={
                    "node_name": "visual_executor",
                    "generation_id": generation_id,
                    "bucket_name": self.bucket_name,
                    "blob_path": blob_path,
                    "credential_source": self.credential_source,
                    "credentials_resolved": self.credentials_resolved,
                    "auth_client": type(self.client).__name__ if self.client is not None else None,
                    "final_url": final_url,
                },
            )
            return final_url
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "v3 visual gcs upload failed",
                extra={
                    "node_name": "visual_executor",
                    "generation_id": generation_id,
                    "bucket_name": self.bucket_name,
                    "blob_path": blob_path,
                    "credential_source": self.credential_source,
                    "credentials_resolved": self.credentials_resolved,
                    "auth_client": type(self.client).__name__ if self.client is not None else None,
                },
                exc_info=exc,
            )
            raise

    async def store_image_key(
        self,
        *,
        key: str,
        image_bytes: bytes,
        content_type: str = "image/png",
    ) -> str:
        final_url = await self._core_store.upload_with_key(
            key=key,
            image_bytes=image_bytes,
            content_type=content_type,
        )
        if not final_url:
            raise RuntimeError("GCS upload returned no URL")
        return final_url

    async def image_exists(self, *, key: str) -> bool:
        return await self._core_store.exists(key=key)

    async def copy_image(self, *, source_key: str, destination_key: str) -> str | None:
        return await self._core_store.copy(
            source_key=source_key,
            destination_key=destination_key,
        )

    async def probe_write_access(self) -> tuple[bool, str]:
        return await asyncio.to_thread(self._core_probe)

    def _core_probe(self) -> tuple[bool, str]:
        bucket = self._core_store._bucket
        if bucket is None:
            return False, "GCS bucket is not configured"
        if not bucket.exists():
            return False, f"GCS bucket '{self.bucket_name}' is not accessible"

        permissions = bucket.test_iam_permissions(["storage.objects.create"])
        if "storage.objects.create" not in permissions:
            return (
                False,
                f"GCS bucket '{self.bucket_name}' is missing storage.objects.create permission",
            )

        return (
            True,
            f"GCS bucket '{self.bucket_name}' writable via {self.credential_source}",
        )

    def describe_target(self) -> str:
        if self.base_url:
            return f"gcs:{self.bucket_name} base_url={self.base_url}"
        return f"gcs:{self.bucket_name} auth={self.credential_source}"


def get_image_store() -> ImageStore:
    env = settings.app_env
    if env in PRODUCTION_LIKE_ENVS:
        return GCSImageStore(bucket_name=settings.gcs_bucket_name)
    return LocalImageStore(
        base_path=Path("data/images"),
        base_url=_resolve_local_storage_base_url(),
    )

