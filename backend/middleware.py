"""HTTP middleware: request IDs, structured access logs, security headers, body-size limits,
and a consistent error envelope.

Error envelope (all non-2xx JSON responses):
    {"error": {"code": "...", "message": "...", "request_id": "..."}, "detail": <legacy>}
`detail` is kept for backward compatibility with existing frontend consumers that read it.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.config import settings

access_logger = logging.getLogger("pashu_shield.access")
logger = logging.getLogger("pashu_shield")

REDACT_KEYS = {"password", "token", "access_token", "refresh_token", "authorization", "api_key", "secret"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update({k: ("[REDACTED]" if k.lower() in REDACT_KEYS else v) for k, v in extra.items()})
        if record.exc_info and not settings.is_production:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def _code_for_status(status: int) -> str:
    return {400: "BAD_REQUEST", 401: "NOT_AUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT",
            413: "PAYLOAD_TOO_LARGE", 415: "UNSUPPORTED_MEDIA_TYPE", 422: "VALIDATION_ERROR", 429: "RATE_LIMITED"}.get(status, "ERROR" if status < 500 else "INTERNAL_ERROR")


def error_body(request: Request, status: int, detail: Any) -> dict:
    code, message = _code_for_status(status), None
    if isinstance(detail, dict):
        code = detail.get("code", code)
        message = detail.get("message")
    elif isinstance(detail, str):
        message = detail
    message = message or "Request failed"
    return {"error": {"code": code, "message": message, "request_id": getattr(request.state, "request_id", None)}, "detail": message if not isinstance(detail, list) else detail}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        if len(request_id) > 64 or not request_id.replace("-", "").isalnum():
            request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        request.state.trace_id = request.headers.get("traceparent", request_id)

        length = request.headers.get("content-length")
        limit = settings.MAX_UPLOAD_BYTES if request.url.path.endswith("/upload") or "/files" in request.url.path or "/voice/recordings" in request.url.path else settings.MAX_REQUEST_BYTES
        if length and length.isdigit() and int(length) > limit:
            return JSONResponse(status_code=413, content=error_body(request, 413, "Request body too large"), headers={"X-Request-ID": request_id})

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error", extra={"fields": {"request_id": request_id, "path": request.url.path}})
            response = JSONResponse(status_code=500, content=error_body(request, 500, "Internal server error"))
        latency_ms = round((time.perf_counter() - start) * 1000, 1)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(self), camera=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'" if request.url.path.startswith("/api") else response.headers.get("Content-Security-Policy", "frame-ancestors 'none'")
        if request.url.path.startswith("/api") and request.method == "GET":
            response.headers.setdefault("Cache-Control", "no-store")
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        access_logger.info("request", extra={"fields": {
            "request_id": request_id, "trace_id": request.state.trace_id, "method": request.method,
            "endpoint": request.url.path, "status": response.status_code, "latency_ms": latency_ms,
            "user_id": getattr(request.state, "user_id", None),
        }})
        return response


class HTTPSRedirectInProduction(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        if settings.is_production and proto != "https" and request.url.path not in {"/live", "/ready", "/health"}:
            return JSONResponse(status_code=400, content=error_body(request, 400, "HTTPS is required"))
        return await call_next(request)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exc(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content=error_body(request, exc.status_code, exc.detail), headers=getattr(exc, "headers", None))

    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exc(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content=error_body(request, exc.status_code, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_exc(request: Request, exc: RequestValidationError):
        errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
        body = error_body(request, 422, {"code": "VALIDATION_ERROR", "message": "Request validation failed"})
        body["error"]["fields"] = errors
        body["detail"] = errors
        return JSONResponse(status_code=422, content=body)
