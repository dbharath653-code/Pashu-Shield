import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db
from backend.models import User, UserRole, UserSession
from backend.schemas import (
    FarmerRegister, VetRegister, LabRegister,
    UserLogin, TokenResponse, UserProfile
)
from backend.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user
)
from backend.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup/farmer", response_model=TokenResponse)
async def signup_farmer(req: FarmerRegister, db: AsyncSession = Depends(get_db)):
    # Normalize email or create a phone-based email identifier
    email = req.email or f"{req.phone}@pashushield.gov.in"
    
    # Check existing user
    stmt = select(User).where((User.email == email) | (User.phone == req.phone))
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this phone or email already registered")
        
    user_id = f"FARMER-{uuid.uuid4().hex[:8].upper()}"
    user = User(
        id=user_id,
        email=email,
        phone=req.phone,
        hashed_password=hash_password(req.password),
        role=UserRole.FARMER.value,
        full_name=req.full_name,
        state="Maharashtra",
        district=req.district,
        taluka=req.taluka,
        village=req.village,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await AuditService.log(
        db, action="USER_SIGNUP", resource="USER", resource_id=user.id,
        user_id=user.id, user_name=user.full_name, role=user.role
    )
    
    access_token = create_access_token({"sub": user.id, "role": user.role, "district": user.district})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "district": user.district, "village": user.village
        }
    }

@router.post("/signup/vet", response_model=TokenResponse)
async def signup_vet(req: VetRegister, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.email == req.email) | (User.phone == req.phone))
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this phone or email already registered")
        
    user_id = f"VET-{uuid.uuid4().hex[:8].upper()}"
    user = User(
        id=user_id,
        email=req.email,
        phone=req.phone,
        hashed_password=hash_password(req.password),
        role=UserRole.VETERINARIAN.value,
        full_name=req.full_name,
        license_number=req.license_number,
        qualification=req.qualification,
        specialization=req.specialization,
        organization=req.organization,
        state="Maharashtra",
        district=req.district,
        taluka=req.taluka,
        service_area=req.service_area or req.district,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await AuditService.log(
        db, action="VET_SIGNUP", resource="USER", resource_id=user.id,
        user_id=user.id, user_name=user.full_name, role=user.role
    )
    
    access_token = create_access_token({"sub": user.id, "role": user.role, "district": user.district})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "district": user.district, "license_number": user.license_number
        }
    }

@router.post("/signup/lab", response_model=TokenResponse)
async def signup_lab(req: LabRegister, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.email == req.email)
    existing = (await db.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already registered")
        
    user_id = f"LAB-{uuid.uuid4().hex[:8].upper()}"
    user = User(
        id=user_id,
        email=req.email,
        phone=req.phone,
        hashed_password=hash_password(req.password),
        role=UserRole.LAB_TECHNICIAN.value,
        full_name=req.lab_name,
        organization=req.lab_name,
        qualification=req.accreditation,
        state="Maharashtra",
        district=req.district,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    await AuditService.log(
        db, action="LAB_SIGNUP", resource="USER", resource_id=user.id,
        user_id=user.id, user_name=user.full_name, role=user.role
    )
    
    access_token = create_access_token({"sub": user.id, "role": user.role, "district": user.district})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id, "email": user.email, "full_name": user.full_name,
            "role": user.role, "district": user.district
        }
    }

@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where((User.email == req.email) | (User.phone == req.email))
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid phone/email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = create_access_token({"sub": user.id, "role": user.role, "district": user.district})
    refresh_token = create_refresh_token({"sub": user.id})
    
    await AuditService.log(
        db, action="USER_LOGIN", resource="USER", resource_id=user.id,
        user_id=user.id, user_name=user.full_name, role=user.role
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
            "district": user.district,
            "village": user.village,
            "license_number": user.license_number,
            "qualification": user.qualification
        }
    }

@router.post("/demo-login/{role}", response_model=TokenResponse)
async def demo_login(role: str, db: AsyncSession = Depends(get_db)):
    """One-tap instant login for evaluation and testing across roles."""
    normalized_role = role.upper()
    role_map = {
        "FARMER": UserRole.FARMER.value,
        "VETERINARIAN": UserRole.VETERINARIAN.value,
        "VET": UserRole.VETERINARIAN.value,
        "LAB": UserRole.LAB_TECHNICIAN.value,
        "LABORATORY": UserRole.LAB_TECHNICIAN.value,
        "DISTRICT": UserRole.DISTRICT_OFFICER.value,
        "DISTRICT_OFFICER": UserRole.DISTRICT_OFFICER.value,
        "STATE": UserRole.STATE_OFFICER.value,
        "STATE_OFFICER": UserRole.STATE_OFFICER.value,
        "ADMIN": UserRole.SYSTEM_ADMIN.value,
        "SYSTEM_ADMIN": UserRole.SYSTEM_ADMIN.value,
    }
    
    target_role = role_map.get(normalized_role, UserRole.FARMER.value)
    
    stmt = select(User).where(User.role == target_role, User.is_active == True)
    user = (await db.execute(stmt)).scalars().first()
    
    if not user:
        # Create user if not existing
        user = User(
            id=f"{target_role}-DEMO-01",
            email=f"{target_role.lower()}@pashushield.gov.in",
            phone="9876543210",
            hashed_password=hash_password("Demo@123"),
            role=target_role,
            full_name=f"Demo {target_role.title().replace('_', ' ')}",
            district="Pune",
            taluka="Shirur",
            village="Walwur",
            state="Maharashtra",
            is_active=True,
            is_verified=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    access_token = create_access_token({"sub": user.id, "role": user.role, "district": user.district})
    refresh_token = create_refresh_token({"sub": user.id})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "role": user.role,
            "district": user.district,
            "village": user.village,
            "license_number": user.license_number,
            "qualification": user.qualification
        }
    }

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
