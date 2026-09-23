"""Notification service: persisted, localised, deduplicated, rate-limited, consent-aware.

Status lifecycle: QUEUED -> SUBMITTED (provider accepted, has message id) -> SENT/DELIVERED/READ
(only from provider callbacks) | FAILED | NOT_CONFIGURED | SUPPRESSED (no consent / dedup).
A message is NEVER marked DELIVERED from the send call itself.

Providers:
  * none      -> NOT_CONFIGURED (nothing is sent; clearly reported)
  * dev_log   -> development only: logs the message, status DEV_LOGGED (refused in production)
  * fast2sms  -> Fast2SMS bulkV2 API (requires SMS_API_KEY; DLT registration is the operator's duty)
  * whatsapp_cloud_api -> Meta WhatsApp Cloud API (requires token, phone number id, approved templates)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Notification, User

logger = logging.getLogger("pashu_shield.notify")

TEMPLATES: Dict[str, Dict[str, str]] = {
    "HIGH_RISK_ALERT": {
        "en": "PASHU-SHIELD ALERT: {risk} risk report for {disease} in {village}, {district}. Isolate sick animals and call 1962.",
        "hi": "पशु-शील्ड चेतावनी: {village}, {district} में {disease} का {risk} जोखिम। बीमार पशुओं को अलग करें, 1962 पर कॉल करें।",
        "mr": "पशु-शील्ड इशारा: {village}, {district} येथे {disease} चा {risk} धोका. आजारी जनावरे वेगळी ठेवा, 1962 वर कॉल करा.",
    },
    "VETERINARIAN_ASSIGNED": {
        "en": "PASHU-SHIELD: Case #{case_number} has been offered to you. Please accept or reject in the app.",
        "hi": "पशु-शील्ड: केस #{case_number} आपको सौंपा गया है। कृपया ऐप में स्वीकार या अस्वीकार करें।",
        "mr": "पशु-शील्ड: केस #{case_number} तुम्हाला देण्यात आली आहे. कृपया अ‍ॅपमध्ये स्वीकारा किंवा नाकारा.",
    },
    "REPORT_RECEIVED": {
        "en": "PASHU-SHIELD: Report {report_number} received. Triage: {risk}. Track status in the app.",
        "hi": "पशु-शील्ड: रिपोर्ट {report_number} प्राप्त। जोखिम: {risk}।",
        "mr": "पशु-शील्ड: अहवाल {report_number} मिळाला. धोका: {risk}.",
    },
    "CASE_STATUS_UPDATED": {"en": "PASHU-SHIELD: Your case #{case_number} status changed to: {status}."},
    "LAB_RESULT_READY": {"en": "PASHU-SHIELD: Lab result for sample #{sample_code} has been verified and released."},
    "VACCINATION_DUE": {"en": "PASHU-SHIELD: {disease} vaccination for animal {animal_id} is due on {due_date}."},
}


def render(template: str, language: str, context: Dict[str, Any]) -> tuple[str, str]:
    variants = TEMPLATES.get(template)
    if not variants:
        raise ValueError(f"Unknown notification template {template}")
    lang = language if language in variants else "en"
    safe = {k: str(v)[:80] for k, v in context.items()}
    try:
        return variants[lang].format(**safe), lang
    except KeyError as e:
        raise ValueError(f"Missing template variable {e}")


class ProviderResult(dict):
    pass


class BaseChannel:
    channel = "BASE"
    provider = "none"

    def configured(self) -> bool:
        return False

    async def send(self, recipient: str, message: str, template: str, language: str) -> ProviderResult:
        return ProviderResult(status="NOT_CONFIGURED", provider=self.provider, error=f"No {self.channel} provider configured")


class DevLogChannel(BaseChannel):
    provider = "dev_log"

    def __init__(self, channel: str) -> None:
        self.channel = channel

    def configured(self) -> bool:
        return not settings.is_production

    async def send(self, recipient, message, template, language):
        logger.info("DEV notification (not sent to any network)", extra={"fields": {"channel": self.channel, "template": template, "recipient_tail": recipient[-4:]}})
        return ProviderResult(status="DEV_LOGGED", provider=self.provider, provider_message_id=f"dev-{uuid.uuid4().hex[:12]}")


class Fast2SMSChannel(BaseChannel):
    channel, provider = "SMS", "fast2sms"

    def configured(self) -> bool:
        return bool(settings.SMS_API_KEY)

    async def send(self, recipient, message, template, language):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post("https://www.fast2sms.com/dev/bulkV2", headers={"authorization": settings.SMS_API_KEY},
                                         json={"route": "q", "message": message, "language": "unicode" if language != "en" else "english", "flash": 0, "numbers": recipient})
            body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            if resp.status_code == 200 and body.get("return") is True:
                return ProviderResult(status="SUBMITTED", provider=self.provider, provider_message_id=str(body.get("request_id") or ""))
            return ProviderResult(status="FAILED", provider=self.provider, error=f"HTTP {resp.status_code}: {str(body.get('message'))[:200]}", retryable=resp.status_code >= 500)
        except httpx.HTTPError as e:
            return ProviderResult(status="FAILED", provider=self.provider, error=type(e).__name__, retryable=True)


class WhatsAppCloudChannel(BaseChannel):
    channel, provider = "WHATSAPP", "whatsapp_cloud_api"

    def configured(self) -> bool:
        return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    async def send(self, recipient, message, template, language):
        # Business-initiated messages outside the 24h window require an approved template; the
        # template name in Meta must equal our template key in lower-case.
        url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "template",
                   "template": {"name": template.lower(), "language": {"code": language}, "components": [{"type": "body", "parameters": [{"type": "text", "text": message[:1000]}]}]}}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(url, headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}, json=payload)
            body = resp.json() if resp.content else {}
            if resp.status_code == 200 and body.get("messages"):
                return ProviderResult(status="SUBMITTED", provider=self.provider, provider_message_id=body["messages"][0].get("id"))
            err = (body.get("error") or {}).get("message", f"HTTP {resp.status_code}")
            return ProviderResult(status="FAILED", provider=self.provider, error=str(err)[:200], retryable=resp.status_code >= 500)
        except httpx.HTTPError as e:
            return ProviderResult(status="FAILED", provider=self.provider, error=type(e).__name__, retryable=True)


def channel_for(name: str) -> BaseChannel:
    name = name.upper()
    if name == "SMS":
        if settings.SMS_PROVIDER == "fast2sms":
            return Fast2SMSChannel()
        if settings.SMS_PROVIDER == "dev_log":
            return DevLogChannel("SMS")
    if name == "WHATSAPP":
        if settings.WHATSAPP_PROVIDER == "whatsapp_cloud_api":
            return WhatsAppCloudChannel()
        if settings.WHATSAPP_PROVIDER == "dev_log":
            return DevLogChannel("WHATSAPP")
    c = BaseChannel()
    c.channel = name
    return c


def verify_whatsapp_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    if not settings.WHATSAPP_APP_SECRET or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(settings.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.split("=", 1)[1])


class NotificationService:
    @staticmethod
    async def queue(db: AsyncSession, *, channel: str, template: str, context: Dict[str, Any], user: Optional[User] = None,
                    recipient: Optional[str] = None, dedup_key: Optional[str] = None, require_consent: bool = True) -> Notification:
        """Persist a notification (status QUEUED) and enqueue delivery. Caller commits."""
        from backend.services.jobs import enqueue
        language = (getattr(user, "notification_language", None) or "en")
        message, language = render(template, language, context)
        target = recipient or (user.phone if user and channel.upper() in ("SMS", "WHATSAPP") else getattr(user, "id", None)) or ""
        if dedup_key:
            existing = (await db.execute(select(Notification).where(Notification.dedup_key == dedup_key))).scalars().first()
            if existing:
                return existing
        n = Notification(id=f"NTF-{uuid.uuid4().hex[:12].upper()}", user_id=getattr(user, "id", None), channel=channel.upper(), template=template, language=language,
                         recipient=target, content=message, status="QUEUED", dedup_key=dedup_key, created_at=datetime.utcnow())
        consent_attr = {"SMS": "sms_opt_in", "WHATSAPP": "whatsapp_opt_in"}.get(channel.upper())
        if require_consent and consent_attr and user is not None and not getattr(user, consent_attr, False):
            n.status, n.failure_reason = "SUPPRESSED", "Recipient has not opted in to this channel"
        elif channel.upper() in ("SMS", "WHATSAPP") and not target:
            n.status, n.failure_reason = "FAILED", "No recipient phone number"
        db.add(n)
        await db.flush()
        if n.status == "QUEUED":
            if channel.upper() == "IN_APP":
                n.status, n.provider = "DELIVERED", "in_app"
                n.delivered_at = datetime.utcnow()
            else:
                await enqueue(db, "notification.deliver", {"notification_id": n.id}, dedup_key=f"deliver:{n.id}")
        return n

    @staticmethod
    async def deliver(db: AsyncSession, notification_id: str) -> Dict[str, Any]:
        """Job handler. Raises RetryableError for transient failures so the job system retries."""
        from backend.services.jobs import RetryableError
        from backend.services.external_data_service import record_health
        n = await db.get(Notification, notification_id)
        if n is None or n.status not in ("QUEUED", "FAILED"):
            return {"skipped": True}
        ch = channel_for(n.channel)
        n.attempts += 1
        res = await ch.send(n.recipient, n.content, n.template, n.language or "en")
        n.provider = res.get("provider")
        n.delivery_details = {k: v for k, v in res.items() if k != "retryable"}
        n.status = res["status"]
        n.provider_message_id = res.get("provider_message_id")
        n.failure_reason = res.get("error")
        if n.status in ("SUBMITTED", "DEV_LOGGED"):
            n.sent_at = datetime.utcnow()
        await db.commit()
        key = f"{n.channel}_{ch.provider}".upper()
        if n.status == "SUBMITTED":
            await record_health(key, "notification", ok=True, records=1)
        elif n.status == "FAILED":
            await record_health(key, "notification", ok=False, error=n.failure_reason)
        elif n.status == "NOT_CONFIGURED":
            await record_health(f"{n.channel}", "notification", ok=False, error="not configured", configured=False, state="CONFIGURATION_REQUIRED")
        if n.status == "FAILED" and res.get("retryable"):
            raise RetryableError(n.failure_reason or "provider failure")
        return {"status": n.status}

    @staticmethod
    async def apply_status_callback(db: AsyncSession, provider_message_id: str, status: str, error: Optional[str] = None) -> bool:
        mapping = {"sent": "SENT", "delivered": "DELIVERED", "read": "READ", "failed": "FAILED"}
        n = (await db.execute(select(Notification).where(Notification.provider_message_id == provider_message_id))).scalars().first()
        if not n or status.lower() not in mapping:
            return False
        order = ["QUEUED", "SUBMITTED", "SENT", "DELIVERED", "READ"]
        new = mapping[status.lower()]
        if new == "FAILED" or (n.status in order and order.index(new) > order.index(n.status)):
            n.status = new
            if new == "DELIVERED":
                n.delivered_at = datetime.utcnow()
            if error:
                n.failure_reason = error[:500]
            await db.commit()
        return True

    # ---- backward compatibility for older call sites ------------------------------------
    @classmethod
    async def dispatch(cls, channel: str, recipient: str, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated synchronous path. Does not claim delivery."""
        ch = channel_for(channel)
        try:
            message, lang = render(template_name, "en", context)
        except ValueError as e:
            return {"status": "FAILED", "error": str(e)}
        res = await ch.send(recipient, message, template_name, lang)
        return {"channel": channel, "template": template_name, "delivery": dict(res), "timestamp": datetime.utcnow().isoformat()}
