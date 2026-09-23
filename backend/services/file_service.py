"""Secure file storage for uploads (voice reports, lab documents, photos).

* Validates declared MIME, extension AND magic bytes; rejects executables/scripts.
* Enforces size limits; stores under a random key (user filename is never used on disk).
* Malware scanning via ClamAV (INSTREAM) when CLAMAV_HOST is set. Without a scanner, uploads
  are refused in production and marked NOT_SCANNED in development.
* Voice recordings get an expiry (retention policy) and are purged by the cleanup job.
* Downloads are authorised per request (owner / jurisdiction), never served from a public path.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import struct
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile

from backend.config import settings

ALLOWED = {
    # content-type: (extensions, signature check)
    "audio/webm": ({".webm"}, lambda b: b.startswith(b"\x1a\x45\xdf\xa3")),
    "audio/ogg": ({".ogg", ".oga", ".opus"}, lambda b: b.startswith(b"OggS")),
    "audio/wav": ({".wav"}, lambda b: b[:4] == b"RIFF" and b[8:12] == b"WAVE"),
    "audio/mpeg": ({".mp3"}, lambda b: b.startswith(b"ID3") or (len(b) > 1 and b[0] == 0xFF and (b[1] & 0xE0) == 0xE0)),
    "audio/mp4": ({".m4a", ".mp4"}, lambda b: b[4:8] == b"ftyp"),
    "image/jpeg": ({".jpg", ".jpeg"}, lambda b: b.startswith(b"\xff\xd8\xff")),
    "image/png": ({".png"}, lambda b: b.startswith(b"\x89PNG\r\n\x1a\n")),
    "application/pdf": ({".pdf"}, lambda b: b.startswith(b"%PDF-")),
}
PURPOSE_TYPES = {
    "VOICE_REPORT": {"audio/webm", "audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4"},
    "LAB_DOCUMENT": {"application/pdf", "image/jpeg", "image/png"},
    "REPORT_PHOTO": {"image/jpeg", "image/png"},
}
FORBIDDEN_SIGNATURES = (b"MZ", b"\x7fELF", b"#!", b"PK\x03\x04", b"<?php", b"<script", b"<html")


def _reject(code: str, message: str, status: int = 415) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def validate_upload(filename: str, content_type: str, head: bytes, purpose: str) -> str:
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct == "audio/x-wav":
        ct = "audio/wav"
    if purpose not in PURPOSE_TYPES:
        raise _reject("INVALID_PURPOSE", "Unknown upload purpose", 422)
    if ct not in PURPOSE_TYPES[purpose]:
        raise _reject("UNSUPPORTED_MEDIA_TYPE", f"{ct or 'unknown'} is not allowed for {purpose}")
    ext = Path(filename or "").suffix.lower()
    exts, sig = ALLOWED[ct]
    if ext not in exts:
        raise _reject("EXTENSION_MISMATCH", f"File extension {ext or '(none)'} does not match {ct}")
    if any(head.lstrip().lower().startswith(s.lower()) for s in FORBIDDEN_SIGNATURES) and not sig(head):
        raise _reject("EXECUTABLE_REJECTED", "Executable or script content is not allowed")
    if not sig(head):
        raise _reject("SIGNATURE_MISMATCH", "File content does not match its declared type")
    return ct


async def clamav_scan(data: bytes) -> str:
    if not settings.CLAMAV_HOST:
        return "NOT_SCANNED"
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=5)
        writer.write(b"zINSTREAM\0")
        for i in range(0, len(data), 65536):
            chunk = data[i:i + 65536]
            writer.write(struct.pack(">I", len(chunk)) + chunk)
        writer.write(struct.pack(">I", 0))
        await writer.drain()
        reply = (await asyncio.wait_for(reader.read(4096), timeout=30)).decode(errors="ignore")
        writer.close()
        return "CLEAN" if reply.strip().endswith("OK") else ("INFECTED" if "FOUND" in reply else "SCAN_ERROR")
    except (OSError, asyncio.TimeoutError):
        return "SCAN_ERROR"


async def save_upload(upload: UploadFile, purpose: str) -> Tuple[str, str, int, str, str]:
    """Returns (storage_key, content_type, size, sha256, scan_status)."""
    data = await upload.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise _reject("PAYLOAD_TOO_LARGE", f"File exceeds {settings.MAX_UPLOAD_BYTES} bytes", 413)
    if not data:
        raise _reject("EMPTY_FILE", "Empty file", 422)
    ct = validate_upload(upload.filename or "", upload.content_type or "", data[:64], purpose)
    scan = await clamav_scan(data)
    if scan == "INFECTED":
        raise _reject("MALWARE_DETECTED", "File rejected by malware scanner", 422)
    if scan in ("NOT_SCANNED", "SCAN_ERROR") and not settings.allow_unscanned_uploads:
        raise _reject("SCANNER_UNAVAILABLE", "Malware scanner unavailable; upload refused", 503)
    key = f"{purpose.lower()}/{datetime.utcnow():%Y/%m}/{secrets.token_hex(16)}{sorted(ALLOWED[ct][0])[0]}"
    path = Path(settings.UPLOAD_DIR) / key
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return key, ct, len(data), hashlib.sha256(data).hexdigest(), scan


def resolve_path(storage_key: str) -> Path:
    root = Path(settings.UPLOAD_DIR).resolve()
    p = (root / storage_key).resolve()
    if root not in p.parents:
        raise _reject("INVALID_KEY", "Invalid storage key", 400)
    return p


def retention_for(purpose: str) -> Optional[datetime]:
    if purpose == "VOICE_REPORT":
        return datetime.utcnow() + timedelta(days=settings.VOICE_RECORDING_RETENTION_DAYS)
    return None


def new_file_id() -> str:
    return f"FILE-{uuid.uuid4().hex[:16].upper()}"
