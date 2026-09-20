import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from backend.config import settings

class NotificationProvider:
    async def send(self, recipient: str, message: str, template: str, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class SMSProvider(NotificationProvider):
    async def send(self, recipient: str, message: str, template: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if settings.SMS_PROVIDER == "fast2sms" and settings.SMS_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        "https://www.fast2sms.com/dev/bulkV2",
                        headers={"authorization": settings.SMS_API_KEY},
                        json={
                            "route": "v3",
                            "sender_id": settings.SMS_SENDER_ID,
                            "message": message,
                            "language": "english",
                            "flash": 0,
                            "numbers": recipient
                        }
                    )
                    return {
                        "status": "DELIVERED" if resp.status_code == 200 else "FAILED",
                        "provider": "fast2sms",
                        "response_code": resp.status_code,
                        "raw": resp.text[:200]
                    }
            except Exception as e:
                return {"status": "FAILED", "provider": "fast2sms", "error": str(e)}
        else:
            # Standalone/Sandbox mock adapter
            return {
                "status": "DELIVERED",
                "provider": "mock_sms_gateway",
                "mode": "DEVELOPMENT_SIMULATION",
                "notice": "Official SMS gateway requires active SMS_API_KEY",
                "sent_message": message
            }

class WhatsAppProvider(NotificationProvider):
    async def send(self, recipient: str, message: str, template: str, data: Dict[str, Any]) -> Dict[str, Any]:
        if settings.WHATSAPP_PROVIDER == "whatsapp_cloud_api" and settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
            try:
                url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
                headers = {
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient,
                    "type": "text",
                    "text": {"body": message}
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    return {
                        "status": "DELIVERED" if resp.status_code == 200 else "FAILED",
                        "provider": "meta_whatsapp_cloud_api",
                        "response_code": resp.status_code,
                        "raw": resp.text[:200]
                    }
            except Exception as e:
                return {"status": "FAILED", "provider": "meta_whatsapp_cloud_api", "error": str(e)}
        else:
            return {
                "status": "DELIVERED",
                "provider": "mock_whatsapp_adapter",
                "mode": "DEVELOPMENT_SIMULATION",
                "notice": "Official WhatsApp requires Meta Business Cloud API access token",
                "recipient": recipient
            }

class NotificationService:
    sms = SMSProvider()
    whatsapp = WhatsAppProvider()

    TEMPLATES = {
        "HIGH_RISK_ALERT": "🚨 PASHU-SHIELD ALERT: High-risk {disease} reported in your village {village}, {district}. Ensure isolation and contact Helpline 1962.",
        "VETERINARIAN_ASSIGNED": "👨‍⚕️ PASHU-SHIELD: Dr. {vet_name} has been assigned to your case #{case_number}. Contact: {vet_phone}.",
        "CASE_STATUS_UPDATED": "📋 PASHU-SHIELD: Your case #{case_number} status changed to: {status}.",
        "LAB_RESULT_READY": "🧪 PASHU-SHIELD: Lab test for sample #{sample_code} is VERIFIED: Result is {result}.",
        "VACCINATION_DUE": "💉 PASHU-SHIELD: Scheduled booster vaccination for {species} against {disease} is due on {due_date}."
    }

    @classmethod
    async def dispatch(
        cls,
        channel: str,
        recipient: str,
        template_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        template = cls.TEMPLATES.get(template_name, "PASHU-SHIELD Notification: {message}")
        message = template.format(**context)
        
        delivery_res = {}
        if channel.upper() == "SMS":
            delivery_res = await cls.sms.send(recipient, message, template_name, context)
        elif channel.upper() == "WHATSAPP":
            delivery_res = await cls.whatsapp.send(recipient, message, template_name, context)
        else:
            delivery_res = {"status": "DELIVERED", "provider": "in_app", "message": message}

        return {
            "notification_id": str(uuid.uuid4()),
            "channel": channel,
            "recipient": recipient,
            "template": template_name,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "delivery": delivery_res
        }
