"""Authentication: signup, login, refresh-token rotation, logout, sessions.

Removed (security): the hardcoded government/admin password bypass, self-service promotion to
STATE_OFFICER/SYSTEM_ADMIN, automatic verification of professional accounts, and the
unconditional demo-login endpoint (now only available when ENABLE_DEMO_LOGIN=true outside
production, and only for pre-seeded is_demo accounts).
"""
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import User, UserRole, UserSession
from backend.schemas import (FarmerRegister, GovernmentRegister, LabRegister, RefreshRequest, TokenResponse,
                             UserLogin, UserProfile, VetRegister)
from backend.security import (decode_token, get_current_user, hash_password, issue_session, revoke_all_user_sessions,
                              rotate_refresh_token, validate_password_strength, verify_password_constant_time)
from backend.services.audit_service import AuditService
from backend.services.rate_limit import client_ip, enforce, limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


def user_payload(user: User) -> Dict[str, Any]:
    return {
        "id": user.id, "email": user.email, "phone": user.phone, "full_name": user.full_name, "role": user.role,
        "district": user.district, "taluka": user.taluka, "village": user.village, "license_number": user.license_number,
        "qualification": user.qualification, "designation": user.designation, "is_verified": user.is_verified, "is_demo": user.is_demo,
    }


async def _token_response(db: AsyncSession, user: User, request: Request, device_id: str = None) -> Dict[str, Any]:
    tokens = await issue_session(db, user, request, device_id=device_id)
    await db.commit()
    return {"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"], "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "user": user_payload(user)}


async def _ensure_unique(db: AsyncSession, email: str, phone: str = None) -> None:
    cond = User.email == email.lower()
    if phone:
        cond = cond | (User.phone == phone)
    if (await db.execute(select(User.id).where(cond))).first():
        # Generic message avoids confirming which identifier exists.
        raise HTTPException(status_code=409, detail={"code": "ACCOUNT_EXISTS", "message": "An account with these details already exists"})


@router.post("/signup/farmer", response_model=TokenResponse, dependencies=[Depends(limiter("signup"))])
async def signup_farmer(req: FarmerRegister, request: Request, db: AsyncSession = Depends(get_db)):
    validate_password_strength(req.password)
    email = (req.email or f"{req.phone}@phone.pashushield.local").lower()
    await _ensure_unique(db, email, req.phone)
    user = User(id=f"FARMER-{uuid.uuid4().hex[:10].upper()}", email=email, phone=req.phone, hashed_password=hash_password(req.password),
                role=UserRole.FARMER.value, full_name=req.full_name, state="Maharashtra", district=req.district, taluka=req.taluka,
                village=req.village, is_active=True, is_verified=True, notification_language=req.notification_language or "en",
                sms_opt_in=req.sms_opt_in, whatsapp_opt_in=req.whatsapp_opt_in)
    db.add(user)
    await db.flush()
    await AuditService.for_user(db, user, "USER_SIGNUP", "USER", user.id, request=request, commit=False)
    return await _token_response(db, user, request)


@router.post("/signup/vet", response_model=TokenResponse, dependencies=[Depends(limiter("signup"))])
async def signup_vet(req: VetRegister, request: Request, db: AsyncSession = Depends(get_db)):
    validate_password_strength(req.password)
    await _ensure_unique(db, req.email, req.phone)
    user = User(id=f"VET-{uuid.uuid4().hex[:10].upper()}", email=req.email.lower(), phone=req.phone, hashed_password=hash_password(req.password),
                role=UserRole.VETERINARIAN.value, full_name=req.full_name, license_number=req.license_number, qualification=req.qualification,
                specialization=req.specialization, organization=req.organization, state="Maharashtra", district=req.district, taluka=req.taluka,
                service_area=req.service_area or req.district, is_active=True, is_verified=False)
    db.add(user)
    await db.flush()
    await AuditService.for_user(db, user, "VET_SIGNUP", "USER", user.id, request=request, commit=False, new_value={"license_number": req.license_number, "pending_verification": True})
    return await _token_response(db, user, request)


@router.post("/signup/lab", response_model=TokenResponse, dependencies=[Depends(limiter("signup"))])
async def signup_lab(req: LabRegister, request: Request, db: AsyncSession = Depends(get_db)):
    validate_password_strength(req.password)
    await _ensure_unique(db, req.email, req.phone)
    user = User(id=f"LAB-{uuid.uuid4().hex[:10].upper()}", email=req.email.lower(), phone=req.phone, hashed_password=hash_password(req.password),
                role=UserRole.LAB_TECHNICIAN.value, full_name=req.lab_name, organization=req.lab_name, qualification=req.accreditation,
                state="Maharashtra", district=req.district, is_active=True, is_verified=False)
    db.add(user)
    await db.flush()
    await AuditService.for_user(db, user, "LAB_SIGNUP", "USER", user.id, request=request, commit=False, new_value={"pending_verification": True})
    return await _token_response(db, user, request)


@router.post("/signup/government", response_model=TokenResponse, dependencies=[Depends(limiter("signup"))])
async def signup_government(req: GovernmentRegister, request: Request, db: AsyncSession = Depends(get_db)):
    """Creates an UNVERIFIED officer account. SYSTEM_ADMIN can never be self-assigned; state-level
    access must be granted by an existing administrator via /users/{id}/verify."""
    validate_password_strength(req.password)
    await _ensure_unique(db, req.email, req.phone)
    requested = (req.role or "").upper()
    role = {"BLOCK_OFFICER": UserRole.BLOCK_OFFICER.value, "STATE_OFFICER": UserRole.STATE_OFFICER.value}.get(requested, UserRole.DISTRICT_OFFICER.value)
    user = User(id=f"GOVT-{uuid.uuid4().hex[:10].upper()}", email=req.email.lower(), phone=req.phone, hashed_password=hash_password(req.password),
                role=role, full_name=req.full_name, department=req.department, designation=req.designation, jurisdiction=req.jurisdiction,
                district=req.district, taluka=req.taluka, state="Maharashtra", is_active=True, is_verified=False)
    db.add(user)
    await db.flush()
    await AuditService.for_user(db, user, "GOVT_SIGNUP", "USER", user.id, request=request, commit=False, new_value={"requested_role": requested, "assigned_role": role, "pending_verification": True})
    return await _token_response(db, user, request)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(limiter("login"))])
async def login(req: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    identifier = req.email.strip()
    await enforce("login", f"id:{identifier.lower()}")
    user = (await db.execute(select(User).where((User.email == identifier.lower()) | (User.phone == identifier)))).scalars().first()
    now = datetime.utcnow()
    if user and user.locked_until and user.locked_until > now:
        await AuditService.log(db, "LOGIN_LOCKED", "USER", user.id, user_id=user.id, role=user.role, ip_address=client_ip(request), success=False)
        raise HTTPException(status_code=423, detail={"code": "ACCOUNT_LOCKED", "message": "Too many failed attempts. Try again later."})
    if not verify_password_constant_time(req.password, user.hashed_password if user else None):
        if user:
            user.failed_login_count = (user.failed_login_count or 0) + 1
            if user.failed_login_count >= settings.LOGIN_MAX_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                user.failed_login_count = 0
            await AuditService.log(db, "LOGIN_FAILED", "USER", user.id, user_id=user.id, role=user.role, ip_address=client_ip(request), success=False, commit=False)
            await db.commit()
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid phone/email or password"})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"code": "ACCOUNT_DEACTIVATED", "message": "Account is deactivated"})
    if user.is_demo and not (settings.demo_allowed):
        raise HTTPException(status_code=403, detail={"code": "DEMO_DISABLED", "message": "Demo accounts are disabled in this environment"})
    user.failed_login_count, user.locked_until, user.last_login_at = 0, None, now
    await AuditService.for_user(db, user, "USER_LOGIN", "USER", user.id, request=request, commit=False)
    return await _token_response(db, user, request, device_id=req.device_id)


@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(limiter("refresh"))])
async def refresh(req: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user, tokens = await rotate_refresh_token(db, req.refresh_token, request)
    await db.commit()
    return {"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"], "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "user": user_payload(user)}


@router.post("/logout")
async def logout(request: Request, req: RefreshRequest = None, all_devices: bool = False, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    revoked = 0
    if all_devices:
        revoked = await revoke_all_user_sessions(db, current_user.id, "LOGOUT")
    else:
        auth = request.headers.get("authorization", "")
        sid = None
        try:
            sid = decode_token(auth.split(" ", 1)[1]).get("sid") if " " in auth else None
        except Exception:
            sid = None
        if sid:
            session = await db.get(UserSession, sid)
            if session:
                from backend.security import revoke_family
                revoked = await revoke_family(db, session.family_id, "LOGOUT")
                # also mark the current row so its access token is rejected even if already rotated
                session.revoked_reason = "LOGOUT"
                session.revoked_at = session.revoked_at or datetime.utcnow()
    await AuditService.for_user(db, current_user, "USER_LOGOUT", "USER", current_user.id, request=request, commit=False, new_value={"sessions_revoked": revoked})
    await db.commit()
    return {"success": True, "sessions_revoked": revoked}


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(UserSession).where(UserSession.user_id == current_user.id, UserSession.revoked_at.is_(None), UserSession.expires_at > datetime.utcnow()).order_by(UserSession.created_at.desc()))).scalars().all()
    return [{"id": s.id, "created_at": s.created_at.isoformat(), "expires_at": s.expires_at.isoformat(), "user_agent": s.user_agent, "device_id": s.device_id} for s in rows]


@router.post("/demo-login/{role}", response_model=TokenResponse, dependencies=[Depends(limiter("login"))])
async def demo_login(role: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Evaluation-only one-tap login for *seeded demo accounts* (is_demo = true).
    Disabled unless ENABLE_DEMO_LOGIN=true and DATA_MODE is hybrid/demo outside production."""
    if not (settings.ENABLE_DEMO_LOGIN and settings.demo_allowed):
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not found"})
    role_map = {"FARMER": "FARMER", "VETERINARIAN": "VETERINARIAN", "VET": "VETERINARIAN", "LAB": "LAB_TECHNICIAN", "LABORATORY": "LAB_TECHNICIAN",
                "LAB_TECHNICIAN": "LAB_TECHNICIAN", "DISTRICT": "DISTRICT_OFFICER", "DISTRICT_OFFICER": "DISTRICT_OFFICER", "STATE": "STATE_OFFICER",
                "STATE_OFFICER": "STATE_OFFICER", "GOVERNMENT": "STATE_OFFICER", "GOVT": "STATE_OFFICER", "ADMIN": "SYSTEM_ADMIN", "SYSTEM_ADMIN": "SYSTEM_ADMIN"}
    target = role_map.get(role.upper())
    if not target:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Unknown demo role"})
    user = (await db.execute(select(User).where(User.role == target, User.is_demo.is_(True), User.is_active.is_(True)).order_by(User.id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail={"code": "DEMO_NOT_SEEDED", "message": "No demo account seeded for this role (run: python -m backend.seed_demo_data)"})
    await AuditService.for_user(db, user, "DEMO_LOGIN", "USER", user.id, request=request, commit=False)
    return await _token_response(db, user, request)


@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
