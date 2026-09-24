"""
Centralised, validated configuration for the Pashu-Shield backend, worker and ML service.

Rules enforced here:
  * No secret has a hardcoded default. In development/test an *ephemeral* random secret
    is generated per process (tokens do not survive restarts) and a warning is logged.
  * ENVIRONMENT=production refuses to start when required settings are missing or unsafe
    (see `validate_for_environment`). Production never silently downgrades to mocks.
  * DATA_MODE declares whether demo data may exist at all:
        live   -> only real/user-generated data; demo seeding and demo login are refused
        hybrid -> real data plus clearly-labelled demo records (is_demo = true)
        demo   -> evaluation mode
"""
from __future__ import annotations

import logging
import os
import secrets
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("pashu_shield.config")

VALID_ENVIRONMENTS = {"development", "test", "staging", "production"}
VALID_DATA_MODES = {"live", "hybrid", "demo"}


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    try:
        return float(raw) if raw not in (None, "") else default
    except ValueError:
        return default


def _list(name: str, default: str = "") -> List[str]:
    return [item.strip() for item in _env(name, default).split(",") if item.strip()]


class ConfigurationError(RuntimeError):
    """Raised when the process must not start with the current configuration."""


class Settings(BaseModel):
    PROJECT_NAME: str = "Pashu-Shield API"
    VERSION: str = "2.1.0"
    API_V1_STR: str = "/api/v1"

    ENVIRONMENT: str = Field(default_factory=lambda: _env("ENVIRONMENT", "development").lower())
    DATA_MODE: str = Field(default_factory=lambda: _env("DATA_MODE", "hybrid").lower())

    # --- Database -------------------------------------------------------------------
    DATABASE_URL: str = Field(default_factory=lambda: _env("DATABASE_URL", "sqlite+aiosqlite:///./pashu_shield.db"))
    # create_all() is only acceptable for local SQLite development and tests.
    # Production/staging schemas are managed exclusively by Alembic migrations.
    AUTO_CREATE_SCHEMA: Optional[bool] = Field(default_factory=lambda: _bool("AUTO_CREATE_SCHEMA", True) if os.getenv("AUTO_CREATE_SCHEMA") else None)
    SEED_DEMO_DATA: bool = Field(default_factory=lambda: _bool("SEED_DEMO_DATA", False))
    DEMO_USER_PASSWORD: str = Field(default_factory=lambda: _env("DEMO_USER_PASSWORD"))

    # --- Redis / worker ---------------------------------------------------------------
    REDIS_URL: str = Field(default_factory=lambda: _env("REDIS_URL"))
    JOB_BACKEND: str = Field(default_factory=lambda: _env("JOB_BACKEND", "inline").lower())  # inline | worker
    RATE_LIMIT_BACKEND: str = Field(default_factory=lambda: _env("RATE_LIMIT_BACKEND", "memory").lower())  # memory | redis

    # --- Security -------------------------------------------------------------------
    JWT_SECRET: str = Field(default_factory=lambda: _env("JWT_SECRET"))
    JWT_REFRESH_SECRET: str = Field(default_factory=lambda: _env("JWT_REFRESH_SECRET"))
    JWT_ISSUER: str = Field(default_factory=lambda: _env("JWT_ISSUER", "pashu-shield"))
    JWT_AUDIENCE: str = Field(default_factory=lambda: _env("JWT_AUDIENCE", "pashu-shield-clients"))
    JWT_LEEWAY_SECONDS: int = Field(default_factory=lambda: _int("JWT_LEEWAY_SECONDS", 30))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default_factory=lambda: _int("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default_factory=lambda: _int("REFRESH_TOKEN_EXPIRE_DAYS", 14))
    BCRYPT_ROUNDS: int = Field(default_factory=lambda: _int("BCRYPT_ROUNDS", 12))
    ENABLE_DEMO_LOGIN: bool = Field(default_factory=lambda: _bool("ENABLE_DEMO_LOGIN", False))
    LOGIN_MAX_ATTEMPTS: int = Field(default_factory=lambda: _int("LOGIN_MAX_ATTEMPTS", 5))
    LOGIN_LOCKOUT_MINUTES: int = Field(default_factory=lambda: _int("LOGIN_LOCKOUT_MINUTES", 15))

    # --- HTTP -------------------------------------------------------------------------
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: _list("CORS_ORIGINS"))
    TRUSTED_HOSTS: List[str] = Field(default_factory=lambda: _list("TRUSTED_HOSTS"))
    MAX_REQUEST_BYTES: int = Field(default_factory=lambda: _int("MAX_REQUEST_BYTES", 2 * 1024 * 1024))
    MAX_UPLOAD_BYTES: int = Field(default_factory=lambda: _int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
    UPLOAD_DIR: str = Field(default_factory=lambda: _env("UPLOAD_DIR", "./var/uploads"))
    CLAMAV_HOST: str = Field(default_factory=lambda: _env("CLAMAV_HOST"))
    CLAMAV_PORT: int = Field(default_factory=lambda: _int("CLAMAV_PORT", 3310))
    ALLOW_UNSCANNED_UPLOADS: Optional[bool] = Field(default_factory=lambda: _bool("ALLOW_UNSCANNED_UPLOADS", False) if os.getenv("ALLOW_UNSCANNED_UPLOADS") else None)

    # --- Retention --------------------------------------------------------------------
    VOICE_RECORDING_RETENTION_DAYS: int = Field(default_factory=lambda: _int("VOICE_RECORDING_RETENTION_DAYS", 30))
    IDEMPOTENCY_RETENTION_DAYS: int = Field(default_factory=lambda: _int("IDEMPOTENCY_RETENTION_DAYS", 30))
    DISPATCH_ACCEPT_TIMEOUT_MINUTES: int = Field(default_factory=lambda: _int("DISPATCH_ACCEPT_TIMEOUT_MINUTES", 30))

    # --- External integrations ------------------------------------------------------
    GOOGLE_MAPS_API_KEY: str = Field(default_factory=lambda: _env("GOOGLE_MAPS_API_KEY"))
    ROUTING_PROVIDER: str = Field(default_factory=lambda: _env("ROUTING_PROVIDER", "none").lower())  # none | osrm
    OSRM_URL: str = Field(default_factory=lambda: _env("OSRM_URL"))
    NADRES_API_URL: str = Field(default_factory=lambda: _env("NADRES_API_URL"))
    NADRES_API_KEY: str = Field(default_factory=lambda: _env("NADRES_API_KEY"))
    GOVERNMENT_API_URL: str = Field(default_factory=lambda: _env("GOVERNMENT_API_URL"))
    GOVERNMENT_API_KEY: str = Field(default_factory=lambda: _env("GOVERNMENT_API_KEY"))
    LAB_PROVIDER: str = Field(default_factory=lambda: _env("LAB_PROVIDER", "none").lower())
    LAB_API_URL: str = Field(default_factory=lambda: _env("LAB_API_URL"))
    LAB_API_KEY: str = Field(default_factory=lambda: _env("LAB_API_KEY"))
    WEATHER_PROVIDER: str = Field(default_factory=lambda: _env("WEATHER_PROVIDER", "open_meteo").lower())  # open_meteo | none
    WEATHER_API_URL: str = Field(default_factory=lambda: _env("WEATHER_API_URL", "https://api.open-meteo.com/v1"))

    SMS_PROVIDER: str = Field(default_factory=lambda: _env("SMS_PROVIDER", "none").lower())  # none | dev_log | fast2sms
    SMS_API_KEY: str = Field(default_factory=lambda: _env("SMS_API_KEY"))
    SMS_SENDER_ID: str = Field(default_factory=lambda: _env("SMS_SENDER_ID", "PASHU"))
    SMS_DLT_TEMPLATE_IDS: str = Field(default_factory=lambda: _env("SMS_DLT_TEMPLATE_IDS"))

    WHATSAPP_PROVIDER: str = Field(default_factory=lambda: _env("WHATSAPP_PROVIDER", "none").lower())  # none | dev_log | whatsapp_cloud_api
    WHATSAPP_ACCESS_TOKEN: str = Field(default_factory=lambda: _env("WHATSAPP_ACCESS_TOKEN"))
    WHATSAPP_PHONE_NUMBER_ID: str = Field(default_factory=lambda: _env("WHATSAPP_PHONE_NUMBER_ID"))
    WHATSAPP_APP_SECRET: str = Field(default_factory=lambda: _env("WHATSAPP_APP_SECRET"))
    WHATSAPP_VERIFY_TOKEN: str = Field(default_factory=lambda: _env("WHATSAPP_VERIFY_TOKEN"))
    WHATSAPP_API_VERSION: str = Field(default_factory=lambda: _env("WHATSAPP_API_VERSION", "v19.0"))

    # --- Telephony / inbound IVR (Exotel) -------------------------------------------------
    # exotel (real Exotel number + ExoML webhooks) | mock (MockTelephonyProvider, demo/tests
    # — never places a real call). The provider is a transport layer only.
    TELEPHONY_PROVIDER: str = Field(default_factory=lambda: _env("TELEPHONY_PROVIDER", "exotel").lower())
    # Explicit "live Exotel" switch. Must be true for TELEPHONY_PROVIDER=exotel and false for
    # mock, so a real number can never be dialled by accident and a mock can never be
    # mistaken for a live integration.
    EXOTEL_ENABLED: bool = Field(default_factory=lambda: _bool("EXOTEL_ENABLED", False))
    # Exotel API credentials — HTTP Basic Auth (API Key = username, API Token = password).
    # Backend-only; never exposed to the frontend.
    EXOTEL_API_KEY: str = Field(default_factory=lambda: _env("EXOTEL_API_KEY"))
    EXOTEL_API_TOKEN: str = Field(default_factory=lambda: _env("EXOTEL_API_TOKEN"))
    EXOTEL_ACCOUNT_SID: str = Field(default_factory=lambda: _env("EXOTEL_ACCOUNT_SID"))
    # Regional API host: api.in.exotel.com (Mumbai) or api.exotel.com (Singapore).
    EXOTEL_SUBDOMAIN: str = Field(default_factory=lambda: _env("EXOTEL_SUBDOMAIN", "api.in.exotel.com"))
    # Your ExoPhone (virtual number) the farmer dials, and the ExoML app/flow id whose
    # application URL points at POST /api/v1/ivr/incoming.
    EXOTEL_PHONE_NUMBER: str = Field(default_factory=lambda: _env("EXOTEL_PHONE_NUMBER"))
    EXOTEL_APP_ID: str = Field(default_factory=lambda: _env("EXOTEL_APP_ID"))
    # Exotel does not sign ExoML/StatusCallback webhooks. This shared secret is appended to
    # every action URL we return to Exotel (?t=…) and is required on every webhook we accept.
    EXOTEL_WEBHOOK_SECRET: str = Field(default_factory=lambda: _env("EXOTEL_WEBHOOK_SECRET"))
    EXOTEL_VALIDATE_WEBHOOK: bool = Field(default_factory=lambda: _bool("EXOTEL_VALIDATE_WEBHOOK", True))
    # Extra check: confirm an unknown CallSid against Exotel's authenticated Call Details API.
    # Costs one round trip per call; enable when the webhook secret may not stay private.
    EXOTEL_VERIFY_CALL_SID: bool = Field(default_factory=lambda: _bool("EXOTEL_VERIFY_CALL_SID", False))
    EXOTEL_TIMEOUT_SECONDS: float = Field(default_factory=lambda: _float("EXOTEL_TIMEOUT_SECONDS", 10.0))
    # Public https base Exotel reaches (e.g. https://abc.ngrok-free.app) — used to build the
    # absolute ExoML action URLs. Required for real inbound calls.
    PUBLIC_API_BASE_URL: str = Field(default_factory=lambda: _env("PUBLIC_API_BASE_URL"))

    IVR_ENABLED: bool = Field(default_factory=lambda: _bool("IVR_ENABLED", True))
    IVR_DEFAULT_LANGUAGE: str = Field(default_factory=lambda: _env("IVR_DEFAULT_LANGUAGE", "en").lower())
    IVR_VET_TIMEOUT_SECONDS: int = Field(default_factory=lambda: _int("IVR_VET_TIMEOUT_SECONDS", 20))
    IVR_MAX_VET_ATTEMPTS: int = Field(default_factory=lambda: _int("IVR_MAX_VET_ATTEMPTS", 3))
    CALL_RECORDING_ENABLED: bool = Field(default_factory=lambda: _bool("CALL_RECORDING_ENABLED", False))
    # Safe demo endpoints ("Simulate Incoming Farmer Call") — refused in production.
    DEMO_MODE: bool = Field(default_factory=lambda: _bool("DEMO_MODE", False))

    # --- Speech-to-text / AI call summary for IVR recordings -------------------------------
    STT_PROVIDER: str = Field(default_factory=lambda: _env("STT_PROVIDER", "").lower())  # "" | none | openai_whisper
    STT_API_KEY: str = Field(default_factory=lambda: _env("STT_API_KEY"))
    AI_SUMMARY_PROVIDER: str = Field(default_factory=lambda: _env("AI_SUMMARY_PROVIDER", "").lower())  # "" | none | openai
    AI_SUMMARY_API_KEY: str = Field(default_factory=lambda: _env("AI_SUMMARY_API_KEY"))

    TRANSLATION_PROVIDER: str = Field(default_factory=lambda: _env("TRANSLATION_PROVIDER", "local").lower())  # local | google
    TRANSLATION_API_KEY: str = Field(default_factory=lambda: _env("TRANSLATION_API_KEY"))

    # ------------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def demo_allowed(self) -> bool:
        return not self.is_production and self.DATA_MODE in {"hybrid", "demo"}

    @property
    def auto_create_schema(self) -> bool:
        if self.AUTO_CREATE_SCHEMA is not None:
            return self.AUTO_CREATE_SCHEMA and not self.is_production
        return self.ENVIRONMENT in {"development", "test"}

    @property
    def allow_unscanned_uploads(self) -> bool:
        if self.ALLOW_UNSCANNED_UPLOADS is not None:
            return self.ALLOW_UNSCANNED_UPLOADS and not self.is_production
        return not self.is_production


def validate_for_environment(s: Settings) -> List[str]:
    """Validate configuration; raises ConfigurationError for fatal problems, returns warnings."""
    errors: List[str] = []
    warnings: List[str] = []

    if s.ENVIRONMENT not in VALID_ENVIRONMENTS:
        errors.append(f"ENVIRONMENT must be one of {sorted(VALID_ENVIRONMENTS)}")
    if s.DATA_MODE not in VALID_DATA_MODES:
        errors.append(f"DATA_MODE must be one of {sorted(VALID_DATA_MODES)}")

    strict = s.ENVIRONMENT in {"production", "staging"}
    for name in ("JWT_SECRET", "JWT_REFRESH_SECRET"):
        value = getattr(s, name)
        if not value:
            if strict:
                errors.append(f"{name} is required in {s.ENVIRONMENT}")
            else:
                setattr(s, name, secrets.token_urlsafe(48))
                warnings.append(f"{name} not set: generated an ephemeral development secret (tokens reset on restart)")
        elif len(value) < 32:
            (errors if strict else warnings).append(f"{name} must be at least 32 characters")
    if s.JWT_SECRET and s.JWT_SECRET == s.JWT_REFRESH_SECRET:
        (errors if strict else warnings).append("JWT_SECRET and JWT_REFRESH_SECRET must differ")

    if s.is_production:
        if s.DATA_MODE != "live":
            errors.append("Production requires DATA_MODE=live (demo data must never mix with surveillance data)")
        if s.is_sqlite:
            errors.append("Production requires PostgreSQL/PostGIS (DATABASE_URL)")
        if not s.CORS_ORIGINS or "*" in s.CORS_ORIGINS:
            errors.append("Production requires an explicit CORS_ORIGINS allow-list (no '*')")
        if s.ENABLE_DEMO_LOGIN or s.SEED_DEMO_DATA:
            errors.append("ENABLE_DEMO_LOGIN / SEED_DEMO_DATA are forbidden in production")
        if s.JOB_BACKEND != "worker":
            errors.append("Production requires JOB_BACKEND=worker (dedicated `python -m backend.worker` process)")
        if s.RATE_LIMIT_BACKEND != "redis" or not s.REDIS_URL:
            errors.append("Production requires RATE_LIMIT_BACKEND=redis (in-memory limits are per-process)")
        for provider, keys in (
            ("SMS_PROVIDER", {"fast2sms": ["SMS_API_KEY"]}),
            ("WHATSAPP_PROVIDER", {"whatsapp_cloud_api": ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_APP_SECRET"]}),
            ("TRANSLATION_PROVIDER", {"google": ["TRANSLATION_API_KEY"]}),
            ("ROUTING_PROVIDER", {"osrm": ["OSRM_URL"]}),
        ):
            selected = getattr(s, provider)
            if selected == "dev_log":
                errors.append(f"{provider}=dev_log is a development-only adapter")
            for key in keys.get(selected, []):
                if not getattr(s, key):
                    errors.append(f"{provider}={selected} requires {key}")
    if s.SEED_DEMO_DATA and s.DATA_MODE == "live":
        errors.append("SEED_DEMO_DATA is not allowed with DATA_MODE=live")

    # --- Telephony / IVR (Exotel) -----------------------------------------------------------
    if s.TELEPHONY_PROVIDER not in {"exotel", "mock"}:
        errors.append("TELEPHONY_PROVIDER must be 'exotel' or 'mock'")
    if s.DEMO_MODE and s.is_production:
        errors.append("DEMO_MODE is forbidden in production")
    # EXOTEL_ENABLED is an explicit switch: it must agree with TELEPHONY_PROVIDER so a real
    # number can never be dialled by accident, and a mock can never be mistaken for a live
    # integration. There is no silent fallback from "real Exotel failed" to fake data.
    if s.TELEPHONY_PROVIDER == "exotel" and not s.EXOTEL_ENABLED:
        errors.append("TELEPHONY_PROVIDER=exotel requires EXOTEL_ENABLED=true "
                      "(use TELEPHONY_PROVIDER=mock for local development)")
    if s.TELEPHONY_PROVIDER == "mock" and s.EXOTEL_ENABLED:
        errors.append("EXOTEL_ENABLED=true requires TELEPHONY_PROVIDER=exotel")
    if s.TELEPHONY_PROVIDER == "exotel" and s.EXOTEL_ENABLED:
        for key in ("EXOTEL_API_KEY", "EXOTEL_API_TOKEN", "EXOTEL_ACCOUNT_SID", "EXOTEL_PHONE_NUMBER"):
            if not getattr(s, key):
                errors.append(f"TELEPHONY_PROVIDER=exotel requires {key}")
        if s.IVR_ENABLED:
            if not s.PUBLIC_API_BASE_URL:
                errors.append("IVR_ENABLED with a live Exotel number requires PUBLIC_API_BASE_URL "
                              "(ExoML action URLs must be absolute)")
            elif s.is_production and not s.PUBLIC_API_BASE_URL.lower().startswith("https://"):
                errors.append("PUBLIC_API_BASE_URL must be https:// in production "
                              "(Exotel reaches the ExoML application URL over the public internet)")
        if s.EXOTEL_VALIDATE_WEBHOOK and not s.EXOTEL_WEBHOOK_SECRET:
            errors.append("EXOTEL_VALIDATE_WEBHOOK=true requires EXOTEL_WEBHOOK_SECRET "
                          "(Exotel does not sign webhooks; this secret is the trust anchor)")
        if s.is_production:
            if not s.EXOTEL_VALIDATE_WEBHOOK:
                errors.append("Production requires EXOTEL_VALIDATE_WEBHOOK=true")
            if not s.EXOTEL_WEBHOOK_SECRET or len(s.EXOTEL_WEBHOOK_SECRET) < 32:
                errors.append("Production requires EXOTEL_WEBHOOK_SECRET of at least 32 characters")
            if not s.EXOTEL_APP_ID:
                errors.append("Production requires EXOTEL_APP_ID (the ExoML app whose URL points "
                              "at POST /api/v1/ivr/incoming)")
    elif s.IVR_ENABLED and s.EXOTEL_VALIDATE_WEBHOOK and not s.EXOTEL_WEBHOOK_SECRET:
        warnings.append("EXOTEL_WEBHOOK_SECRET not set: Exotel webhooks cannot be verified and will "
                        "be rejected (set it, or set EXOTEL_VALIDATE_WEBHOOK=false for local development)")
    if s.EXOTEL_VERIFY_CALL_SID and not (s.EXOTEL_API_KEY and s.EXOTEL_API_TOKEN and s.EXOTEL_ACCOUNT_SID):
        warnings.append("EXOTEL_VERIFY_CALL_SID=true but Exotel API credentials are not configured; "
                        "call-id verification will fail closed")
    if s.STT_PROVIDER not in {"", "none", "openai_whisper"}:
        errors.append("STT_PROVIDER must be one of '', 'none', 'openai_whisper'")
    if s.STT_PROVIDER == "openai_whisper" and not s.STT_API_KEY:
        (errors if strict else warnings).append("STT_PROVIDER=openai_whisper requires STT_API_KEY")
    if s.AI_SUMMARY_PROVIDER not in {"", "none", "openai"}:
        errors.append("AI_SUMMARY_PROVIDER must be one of '', 'none', 'openai'")
    if s.AI_SUMMARY_PROVIDER == "openai" and not s.AI_SUMMARY_API_KEY:
        (errors if strict else warnings).append("AI_SUMMARY_PROVIDER=openai requires AI_SUMMARY_API_KEY")

    if errors:
        raise ConfigurationError("Invalid configuration:\n  - " + "\n  - ".join(errors))
    for w in warnings:
        logger.warning(w)
    return warnings


settings = Settings()
validate_for_environment(settings)
