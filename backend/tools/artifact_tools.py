from __future__ import annotations

import io
import zipfile
from typing import Iterable

from backend.config.settings import settings
from backend.models.schemas import new_id
from backend.utils.logging import logger


def files_to_zip_bytes(files: Iterable[dict[str, str]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item["path"], item["content"])
    return buffer.getvalue()


def maybe_upload_bytes(path: str, data: bytes, content_type: str = "application/zip") -> str | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    try:
        from supabase import create_client

        client = create_client(settings.supabase_url, settings.supabase_service_role_key)
        client.storage.from_(settings.supabase_storage_bucket).upload(
            path,
            data,
            {"content-type": content_type, "upsert": "true"},
        )
        return path
    except Exception as exc:
        logger.error("Storage upload failed", extra={"error_category": "DATABASE_ERROR"})
        logger.debug(str(exc))
        return None


def artifact_storage_path(run_id: str, name: str) -> str:
    return f"{run_id}/{new_id()}-{name}"
