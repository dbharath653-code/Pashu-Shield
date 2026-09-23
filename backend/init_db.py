"""Schema bootstrap and (optional) demo data seeding.

* init_schema(): in development/test, `create_all` for convenience. In staging/production the
  schema is managed exclusively by Alembic (`alembic upgrade head`).
* seed_demo_data(): ONLY when SEED_DEMO_DATA=true and DATA_MODE is hybrid/demo outside
  production. Every seeded row has is_demo=true and demo accounts use DEMO_USER_PASSWORD
  (no hardcoded passwords). No surveillance figures, outbreaks or alerts are fabricated.

Run manually:  python -m backend.init_db --seed-demo
"""
import asyncio
import sys
from datetime import datetime, timedelta

from sqlalchemy import select, text

from backend.config import settings
from backend.database import AsyncSessionLocal, Base, engine
from backend.models import (Animal, Farm, Herd, Laboratory, User, UserRole, VaccinationCampaign, VeterinarianProfile, VeterinaryFacility)
from backend.security import hash_password

DEMO_USERS = [
    ("DEMO-FARMER-001", "farmer.demo@pashushield.local", "9000000001", UserRole.FARMER, "Demo Farmer", "Pune", "Shirur", "Shirur"),
    ("DEMO-VET-001", "vet.demo@pashushield.local", "9000000002", UserRole.VETERINARIAN, "Demo Veterinarian", "Pune", "Shirur", None),
    ("DEMO-LAB-001", "lab.demo@pashushield.local", "9000000003", UserRole.LAB_TECHNICIAN, "Demo Lab Technician", "Pune", None, None),
    ("DEMO-DISTRICT-001", "district.demo@pashushield.local", "9000000004", UserRole.DISTRICT_OFFICER, "Demo District Officer", "Pune", None, None),
    ("DEMO-STATE-001", "state.demo@pashushield.local", "9000000005", UserRole.STATE_OFFICER, "Demo State Officer", None, None, None),
    ("DEMO-ADMIN-001", "admin.demo@pashushield.local", "9000000006", UserRole.SYSTEM_ADMIN, "Demo System Admin", None, None, None),
]


async def init_schema() -> None:
    if settings.auto_create_schema:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def check_database() -> bool:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True


async def seed_demo_data(force: bool = False) -> int:
    if not (settings.SEED_DEMO_DATA or force) or not settings.demo_allowed:
        return 0
    if not settings.DEMO_USER_PASSWORD:
        raise RuntimeError("DEMO_USER_PASSWORD must be set to seed demo accounts")
    async with AsyncSessionLocal() as db:
        if (await db.execute(select(User.id).where(User.is_demo.is_(True)).limit(1))).first():
            return 0
        pw = hash_password(settings.DEMO_USER_PASSWORD)
        for uid, email, phone, role, name, district, taluka, village in DEMO_USERS:
            db.add(User(id=uid, email=email, phone=phone, hashed_password=pw, role=role.value, full_name=name, district=district, taluka=taluka,
                        village=village, is_active=True, is_verified=True, is_demo=True, license_number="DEMO-LICENSE" if role == UserRole.VETERINARIAN else None))
        await db.flush()
        db.add(VeterinarianProfile(user_id="DEMO-VET-001", availability_status="AVAILABLE", service_radius_km=40.0, specializations=["Cattle", "Buffalo"]))
        db.add(Farm(id="DEMO-FARM-001", owner_id="DEMO-FARMER-001", name="Demo Farm", district="Pune", taluka="Shirur", village="Shirur", is_demo=True))
        db.add(Herd(id="DEMO-HERD-001", farm_id="DEMO-FARM-001", owner_id="DEMO-FARMER-001", species="Cattle", total_animals=12, village="Shirur", district="Pune", taluka="Shirur", is_demo=True))
        for i in range(1, 4):
            db.add(Animal(id=f"DEMO-ANM-00{i}", tag_id=f"DEMO-TAG-00{i}", herd_id="DEMO-HERD-001", owner_id="DEMO-FARMER-001", species="Cattle",
                          breed="Gir", village="Shirur", district="Pune", taluka="Shirur", is_demo=True))
        db.add(Laboratory(id="DEMO-LAB-FAC-001", name="Demo Diagnostic Laboratory (not a real facility)", code="DEMO-LAB", district="Pune", is_demo=True, source="DEMO"))
        db.add(VeterinaryFacility(id="DEMO-FAC-001", name="Demo Veterinary Dispensary (not a real facility)", facility_type="Dispensary", district="Pune", taluka="Shirur", is_demo=True, source="DEMO"))
        now = datetime.utcnow()
        db.add(VaccinationCampaign(id="DEMO-CMP-001", campaign_code="DEMO-NADCP-FMD", name="Demo FMD campaign", disease="FMD", vaccine="FMD vaccine (demo)",
                                   species=["Cattle", "Buffalo"], target_districts=["Pune"], start_date=now - timedelta(days=10), end_date=now + timedelta(days=50),
                                   target_population=1000, is_demo=True))
        await db.commit()
        return len(DEMO_USERS)


async def seed_database() -> None:
    """Backward-compatible entry point used by the API lifespan and tests."""
    await init_schema()
    await seed_demo_data()


if __name__ == "__main__":
    async def _main():
        await init_schema()
        n = await seed_demo_data(force="--seed-demo" in sys.argv)
        print(f"schema ready; demo users seeded: {n}")
    asyncio.run(_main())
