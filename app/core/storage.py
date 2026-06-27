"""Object storage (Cloudflare R2, S3-compatible).

Uploads images to a bucket and returns their public URL. R2 speaks the S3 API,
so we talk to it with boto3. Used by partner onboarding to store store photos in
the bucket instead of stuffing base64 blobs into the database.
"""

import base64
import binascii
import re
import uuid
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

# e.g. "data:image/png;base64,iVBORw0KGgo..."
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w/+.-]+);base64,(?P<data>.+)$", re.DOTALL)

_EXT_BY_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


class StorageError(Exception):
    """The supplied image is malformed or too large (client error -> 400)."""


class StorageUploadError(Exception):
    """The image could not be stored in the bucket (infra error -> 502)."""


@lru_cache(maxsize=1)
def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def _decode_data_url(data_url: str) -> tuple[bytes, str, str]:
    """Return (raw_bytes, content_type, extension) for a base64 data URL."""
    match = _DATA_URL_RE.match(data_url.strip())
    if match is None:
        raise StorageError("Expected a base64 image data URL")
    mime = match.group("mime").lower()
    try:
        raw = base64.b64decode(match.group("data"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise StorageError("Image data is not valid base64") from exc
    if not raw:
        raise StorageError("Image is empty")
    return raw, mime, _EXT_BY_MIME.get(mime, "bin")


def _put_object(key: str, body: bytes, content_type: str) -> None:
    _client().put_object(
        Bucket=settings.r2_bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


async def upload_data_url(data_url: str, *, prefix: str) -> str:
    """Upload a base64 data URL to the bucket and return its public URL.

    If the value is already an http(s) URL it is returned unchanged, so
    re-submitting an existing record is idempotent.
    """
    value = data_url.strip()
    if value.startswith(("http://", "https://")):
        return value

    raw, content_type, ext = _decode_data_url(value)

    max_bytes = settings.upload_max_file_size_mb * 1024 * 1024
    if len(raw) > max_bytes:
        raise StorageError(f"Image is too large (max {settings.upload_max_file_size_mb} MB)")

    key = f"{prefix}/{uuid.uuid4().hex}.{ext}"
    try:
        await run_in_threadpool(_put_object, key, raw, content_type)
    except (BotoCoreError, ClientError) as exc:
        raise StorageUploadError("Could not upload image to storage") from exc

    return f"{settings.r2_public_url.rstrip('/')}/{key}"  # type: ignore[union-attr]
