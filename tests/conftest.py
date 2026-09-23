import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="pashu-test-")
os.environ.update({
    "ENVIRONMENT": "test",
    "DATA_MODE": "hybrid",
    "DATABASE_URL": f"sqlite+aiosqlite:///{_tmp}/test.db",
    "JWT_SECRET": "test-access-secret-0123456789abcdef0123456789",
    "JWT_REFRESH_SECRET": "test-refresh-secret-0123456789abcdef012345678",
    "ENABLE_DEMO_LOGIN": "true",
    "SEED_DEMO_DATA": "true",
    "DEMO_USER_PASSWORD": "Demo-Passw0rd!2026",
    "BCRYPT_ROUNDS": "4",
    "JOB_BACKEND": "inline",
    "UPLOAD_DIR": f"{_tmp}/uploads",
    "CORS_ORIGINS": "http://localhost:5173",
    # Telephony / IVR (real Twilio signature validation against these test credentials)
    "TELEPHONY_PROVIDER": "twilio",
    "TWILIO_ACCOUNT_SID": "ACtest000000000000000000000000000000",
    "TWILIO_AUTH_TOKEN": "test-auth-token-0123456789abcdef0123456789",
    "TWILIO_PHONE_NUMBER": "+15005550006",
    "TWILIO_VALIDATE_WEBHOOK": "true",
    "PUBLIC_API_BASE_URL": "http://test",
    "IVR_ENABLED": "true",
    "IVR_DEFAULT_LANGUAGE": "en",
    "DEMO_MODE": "true",
    "CALL_RECORDING_ENABLED": "false",
})

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from backend.main import app  # noqa: E402
from backend.init_db import seed_database  # noqa: E402
from backend.services import rate_limit  # noqa: E402

DEMO_PASSWORD = os.environ["DEMO_USER_PASSWORD"]


@pytest_asyncio.fixture
async def client():
    await seed_database()
    rate_limit.reset_all()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def login(client, role: str) -> dict:
    res = await client.post(f"/api/v1/auth/demo-login/{role}")
    assert res.status_code == 200, res.text
    return res.json()


async def auth_headers(client, role: str) -> dict:
    return {"Authorization": f"Bearer {(await login(client, role))['access_token']}"}
