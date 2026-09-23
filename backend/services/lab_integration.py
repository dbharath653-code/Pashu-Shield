"""Laboratory (LIS/LIMS) integration layer.

No public API contract exists for state/central veterinary diagnostic LIMS, so no external
contract is invented here. `LabProvider` defines what an adapter must implement; the
internal workflow (registration, custody, results, verification) works fully without one.

LAB_PROVIDER=none         -> NotConfiguredLabProvider (status CONFIGURATION_REQUIRED; nothing pushed)
LAB_PROVIDER=dev_mock     -> DevMockLabProvider (development only; clearly labelled, refused in production)
A real adapter should subclass LabProvider once an authorised API specification is available.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from backend.config import settings


class LabProvider:
    name = "none"
    status = "CONFIGURATION_REQUIRED"

    async def register_sample(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        return {"pushed": False, "status": self.status, "reason": "No LIMS adapter configured; sample tracked in Pashu-Shield only"}

    async def fetch_result(self, external_id: str) -> Dict[str, Any]:
        return {"available": False, "status": self.status}


class DevMockLabProvider(LabProvider):
    name = "dev_mock"
    status = "DEV_ONLY"

    async def register_sample(self, sample):
        if settings.is_production:
            raise RuntimeError("dev_mock LIMS adapter cannot be used in production")
        return {"pushed": True, "status": "DEV_ONLY", "external_id": f"DEVMOCK-{uuid.uuid4().hex[:8]}", "note": "Development mock — not a real laboratory system"}


def get_lab_provider() -> LabProvider:
    if settings.LAB_PROVIDER == "dev_mock" and not settings.is_production:
        return DevMockLabProvider()
    return LabProvider()
