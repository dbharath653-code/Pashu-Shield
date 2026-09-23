"""
Authentication and authorisation primitives.

* Passwords: bcrypt (configurable cost). Raw passwords/tokens are never logged or stored.
* Access tokens: short-lived HS256 JWT with iss/aud/exp/iat/nbf/jti, validated with leeway.
* Refresh tokens: opaque-to-client JWT whose jti maps to a `user_sessions` row storing only a
  SHA-256 hash. Every refresh rotates the token; re-use of a rotated token revokes the whole
  token family (theft detection). Logout revokes the session.
* Authorisation: `Permission` enum + ROLE_PERMISSIONS matrix + jurisdiction helpers. Every
  sensitive endpoint uses `require_permission(...)` and, for record-level access,
  `ensure_can_access_record(...)` / `scope_query(...)`.
"""
from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Set

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import User, UserRole, UserSession

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

# bcrypt only uses the first 72 bytes; reject longer inputs instead of silently truncating.
MAX_PASSWORD_BYTES = 72


# ----------------------------------------------------------------------------------------
# Passwords
# ----------------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError("Password too long")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# Used to equalise timing when the account does not exist.
_DUMMY_HASH = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds=4)).decode()


def verify_password_constant_time(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        verify_password(plain, _DUMMY_HASH)
        return False
    return verify_password(plain, hashed)


def validate_password_strength(password: str) -> None:
    problems = []
    if len(password) < 10:
        problems.append("at least 10 characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        problems.append(f"at most {MAX_PASSWORD_BYTES} bytes")
    if not any(c.isdigit() for c in password):
        problems.append("a digit")
    if not any(c.isalpha() for c in password):
        problems.append("a letter")
    if problems:
        raise HTTPException(status_code=422, detail={"code": "WEAK_PASSWORD", "message": "Password must contain " + ", ".join(problems)})


# ----------------------------------------------------------------------------------------
# Tokens
# ----------------------------------------------------------------------------------------
def _now() -> datetime:
    return datetime.utcnow()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(user: User, session_id: Optional[str] = None, expires_delta: Optional[timedelta] = None) -> str:
    now = _now()
    claims = {
        "sub": user.id,
        "role": user.role,
        "district": user.district,
        "taluka": user.taluka,
        "sid": session_id,
        "type": "access",
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def decode_token(token: str, is_refresh: bool = False) -> Dict[str, Any]:
    secret = settings.JWT_REFRESH_SECRET if is_refresh else settings.JWT_SECRET
    payload = jwt.decode(
        token,
        secret,
        algorithms=[settings.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
        options={"leeway": settings.JWT_LEEWAY_SECONDS, "require_exp": True, "require_sub": True},
    )
    expected = "refresh" if is_refresh else "access"
    if payload.get("type") != expected:
        raise JWTError("wrong token type")
    return payload


async def issue_session(
    db: AsyncSession,
    user: User,
    request: Optional[Request] = None,
    family_id: Optional[str] = None,
    device_id: Optional[str] = None,
) -> Dict[str, str]:
    """Create a refresh-token session (new family unless rotating) and a paired access token."""
    now = _now()
    jti = uuid.uuid4().hex
    family = family_id or uuid.uuid4().hex
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh = jwt.encode(
        {
            "sub": user.id, "type": "refresh", "jti": jti, "fam": family,
            "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
            "iat": now, "nbf": now, "exp": expires,
        },
        settings.JWT_REFRESH_SECRET,
        algorithm=settings.ALGORITHM,
    )
    db.add(UserSession(
        id=jti,
        user_id=user.id,
        family_id=family,
        refresh_token_hash=_hash_token(refresh),
        expires_at=expires,
        user_agent=(request.headers.get("user-agent", "")[:255] if request else None),
        ip_address=(request.client.host if request and request.client else None),
        device_id=device_id,
    ))
    await db.flush()
    return {"access_token": create_access_token(user, session_id=jti), "refresh_token": refresh, "session_id": jti}


class RefreshError(HTTPException):
    def __init__(self, message: str = "Invalid or expired refresh token"):
        super().__init__(status_code=401, detail={"code": "INVALID_REFRESH_TOKEN", "message": message})


async def rotate_refresh_token(db: AsyncSession, refresh_token: str, request: Optional[Request] = None) -> tuple[User, Dict[str, str]]:
    try:
        payload = decode_token(refresh_token, is_refresh=True)
    except JWTError:
        raise RefreshError()

    session = await db.get(UserSession, payload.get("jti"))
    if session is None or session.refresh_token_hash != _hash_token(refresh_token):
        raise RefreshError()

    if session.revoked_at is not None:
        # Re-use of a rotated/revoked token => assume theft; revoke the entire family.
        await revoke_family(db, session.family_id, reason="REUSE_DETECTED")
        await db.commit()
        raise RefreshError("Refresh token reuse detected; all sessions in this family were revoked")

    if session.expires_at < _now():
        raise RefreshError()

    user = await db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise RefreshError()

    tokens = await issue_session(db, user, request, family_id=session.family_id, device_id=session.device_id)
    session.revoked_at = _now()
    session.revoked_reason = "ROTATED"
    session.replaced_by = tokens["session_id"]
    session.last_used_at = _now()
    return user, tokens


async def revoke_family(db: AsyncSession, family_id: str, reason: str) -> int:
    rows = (await db.execute(select(UserSession).where(UserSession.family_id == family_id, UserSession.revoked_at.is_(None)))).scalars().all()
    for row in rows:
        row.revoked_at = _now()
        row.revoked_reason = reason
    return len(rows)


async def revoke_all_user_sessions(db: AsyncSession, user_id: str, reason: str) -> int:
    rows = (await db.execute(select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)))).scalars().all()
    for row in rows:
        row.revoked_at = _now()
        row.revoked_reason = reason
    return len(rows)


# ----------------------------------------------------------------------------------------
# Current user
# ----------------------------------------------------------------------------------------
def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "NOT_AUTHENTICATED", "message": "Could not validate credentials"},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def authenticate_token(db: AsyncSession, token: str) -> User:
    """Validate an access token (HTTP or WebSocket) and return the active user."""
    try:
        payload = decode_token(token)
    except JWTError:
        raise _credentials_exception()
    user = await db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise _credentials_exception()
    sid = payload.get("sid")
    if sid:
        session = await db.get(UserSession, sid)
        # A logged-out session invalidates its access tokens immediately. A *rotated* session
        # is still valid until the short access-token expiry (the replacement is live).
        if session is None or session.revoked_reason in {"LOGOUT", "REUSE_DETECTED", "ADMIN_REVOKED", "PASSWORD_CHANGED", "DEACTIVATED"}:
            raise _credentials_exception()
    return user


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        return await authenticate_token(db, token)
    except HTTPException:
        return None


async def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    if not token:
        raise _credentials_exception()
    user = await authenticate_token(db, token)
    request.state.user_id = user.id
    return user


# ----------------------------------------------------------------------------------------
# Permissions
# ----------------------------------------------------------------------------------------
class Permission(str, enum.Enum):
    REPORT_CREATE = "REPORT_CREATE"
    REPORT_READ = "REPORT_READ"
    REPORT_VERIFY = "REPORT_VERIFY"
    REPORT_ASSIGN = "REPORT_ASSIGN"
    CASE_READ = "CASE_READ"
    CASE_UPDATE = "CASE_UPDATE"
    VET_DISPATCH = "VET_DISPATCH"
    VET_PROFILE_UPDATE = "VET_PROFILE_UPDATE"
    ANIMAL_READ = "ANIMAL_READ"
    ANIMAL_WRITE = "ANIMAL_WRITE"
    LAB_SAMPLE_CREATE = "LAB_SAMPLE_CREATE"
    LAB_SAMPLE_READ = "LAB_SAMPLE_READ"
    LAB_SAMPLE_PROCESS = "LAB_SAMPLE_PROCESS"
    LAB_RESULT_ENTER = "LAB_RESULT_ENTER"
    LAB_RESULT_VERIFY = "LAB_RESULT_VERIFY"
    VACCINATION_RECORD = "VACCINATION_RECORD"
    VACCINATION_READ = "VACCINATION_READ"
    VACCINATION_MANAGE = "VACCINATION_MANAGE"
    GIS_VIEW = "GIS_VIEW"
    SURVEILLANCE_VIEW = "SURVEILLANCE_VIEW"
    ALERT_READ = "ALERT_READ"
    ALERT_MANAGE = "ALERT_MANAGE"
    AUDIT_READ = "AUDIT_READ"
    USER_MANAGE = "USER_MANAGE"
    ADMIN_MANAGE = "ADMIN_MANAGE"
    DATA_SOURCE_VIEW = "DATA_SOURCE_VIEW"
    DATA_INGEST = "DATA_INGEST"
    ML_RUN = "ML_RUN"
    SYNC = "SYNC"
    PII_VIEW = "PII_VIEW"


P = Permission
_FIELD = {P.REPORT_CREATE, P.REPORT_READ, P.ANIMAL_READ, P.ANIMAL_WRITE, P.VACCINATION_READ, P.ALERT_READ, P.SYNC, P.CASE_READ}
_OFFICER = {
    P.REPORT_READ, P.REPORT_VERIFY, P.REPORT_ASSIGN, P.CASE_READ, P.VET_DISPATCH, P.ANIMAL_READ,
    P.LAB_SAMPLE_READ, P.VACCINATION_READ, P.VACCINATION_MANAGE, P.GIS_VIEW, P.SURVEILLANCE_VIEW,
    P.ALERT_READ, P.ALERT_MANAGE, P.AUDIT_READ, P.ML_RUN, P.DATA_SOURCE_VIEW, P.PII_VIEW, P.REPORT_CREATE, P.SYNC,
}
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    UserRole.FARMER.value: set(_FIELD),
    UserRole.PARA_VET.value: _FIELD | {P.CASE_UPDATE, P.VET_PROFILE_UPDATE, P.LAB_SAMPLE_CREATE, P.LAB_SAMPLE_READ, P.VACCINATION_RECORD, P.GIS_VIEW, P.PII_VIEW},
    UserRole.VETERINARIAN.value: _FIELD | {
        P.REPORT_VERIFY, P.CASE_UPDATE, P.VET_PROFILE_UPDATE, P.LAB_SAMPLE_CREATE, P.LAB_SAMPLE_READ,
        P.VACCINATION_RECORD, P.GIS_VIEW, P.SURVEILLANCE_VIEW, P.ML_RUN, P.PII_VIEW,
    },
    UserRole.LAB_TECHNICIAN.value: {P.LAB_SAMPLE_READ, P.LAB_SAMPLE_CREATE, P.LAB_SAMPLE_PROCESS, P.LAB_RESULT_ENTER, P.ALERT_READ, P.SYNC},
    UserRole.LAB_ADMIN.value: {P.LAB_SAMPLE_READ, P.LAB_SAMPLE_CREATE, P.LAB_SAMPLE_PROCESS, P.LAB_RESULT_ENTER, P.LAB_RESULT_VERIFY, P.ALERT_READ, P.SYNC, P.AUDIT_READ},
    UserRole.BLOCK_OFFICER.value: set(_OFFICER),
    UserRole.DISTRICT_OFFICER.value: set(_OFFICER),
    UserRole.STATE_OFFICER.value: _OFFICER | {P.USER_MANAGE, P.DATA_INGEST},
    UserRole.SYSTEM_ADMIN.value: set(Permission),
}

# Lab technicians historically could verify results in this app; keep that ability but make it
# explicit so it can be removed by policy (four-eyes principle) without code changes.
ROLE_PERMISSIONS[UserRole.LAB_TECHNICIAN.value].add(P.LAB_RESULT_VERIFY)

GOVERNMENT_ROLES = {UserRole.BLOCK_OFFICER.value, UserRole.DISTRICT_OFFICER.value, UserRole.STATE_OFFICER.value, UserRole.SYSTEM_ADMIN.value}
VET_ROLES = {UserRole.VETERINARIAN.value, UserRole.PARA_VET.value}
LAB_ROLES = {UserRole.LAB_TECHNICIAN.value, UserRole.LAB_ADMIN.value}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def forbidden(message: str = "You do not have permission to perform this action", code: str = "FORBIDDEN") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": code, "message": message})


def require_permission(*permissions: Permission):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        missing = [p.value for p in permissions if not has_permission(current_user, p)]
        if missing:
            raise forbidden(f"Missing permission: {', '.join(missing)}")
        if current_user.role in GOVERNMENT_ROLES | VET_ROLES | LAB_ROLES and current_user.role != UserRole.SYSTEM_ADMIN.value and not current_user.is_verified:
            raise forbidden("Account pending verification by an administrator", code="ACCOUNT_PENDING_VERIFICATION")
        return current_user
    return checker


def require_roles(allowed_roles: List[str]):
    """Backward-compatible role gate (prefer require_permission)."""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.SYSTEM_ADMIN.value or current_user.role in allowed_roles:
            return current_user
        raise forbidden(f"Required role: {', '.join(allowed_roles)}")
    return role_checker


# ----------------------------------------------------------------------------------------
# Jurisdiction (district / block) scoping
# ----------------------------------------------------------------------------------------
def jurisdiction_scope(user: User) -> Dict[str, Optional[str]]:
    """Returns the geographic scope a user may see. None means unrestricted at that level."""
    if user.role in {UserRole.STATE_OFFICER.value, UserRole.SYSTEM_ADMIN.value}:
        return {"district": None, "taluka": None}
    if user.role == UserRole.BLOCK_OFFICER.value:
        return {"district": user.district, "taluka": user.taluka}
    return {"district": user.district, "taluka": None}


def in_jurisdiction(user: User, district: Optional[str], taluka: Optional[str] = None) -> bool:
    scope = jurisdiction_scope(user)
    if scope["district"] and (district or "").lower() != scope["district"].lower():
        return False
    if scope["taluka"] and (taluka or "").lower() != scope["taluka"].lower():
        return False
    return True


def resolve_district_filter(user: User, requested: Optional[str]) -> Optional[str]:
    """A district query parameter may only narrow, never widen, a user's scope."""
    scope = jurisdiction_scope(user)
    if scope["district"] is None:
        return requested
    if requested and requested.lower() != scope["district"].lower():
        raise forbidden("Requested district is outside your jurisdiction", code="OUT_OF_JURISDICTION")
    return scope["district"]


def ensure_can_access_record(
    user: User,
    *,
    owner_ids: Iterable[Optional[str]] = (),
    district: Optional[str] = None,
    taluka: Optional[str] = None,
    assigned_vet_id: Optional[str] = None,
) -> None:
    """Record-level check: ownership for farmers, assignment/jurisdiction for vets & officers."""
    if user.role == UserRole.SYSTEM_ADMIN.value:
        return
    if user.id in {o for o in owner_ids if o}:
        return
    if user.role == UserRole.FARMER.value:
        raise forbidden("You can only access your own records", code="NOT_OWNER")
    if user.role in VET_ROLES:
        if assigned_vet_id == user.id or (assigned_vet_id is None and in_jurisdiction(user, district)):
            return
        raise forbidden("Record is not assigned to you", code="NOT_ASSIGNED")
    if in_jurisdiction(user, district, taluka):
        return
    raise forbidden("Record is outside your jurisdiction", code="OUT_OF_JURISDICTION")


def mask_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return phone
    digits = str(phone)
    return ("*" * max(0, len(digits) - 4)) + digits[-4:]


def phone_for_viewer(viewer: Optional[User], phone: Optional[str], owner_id: Optional[str] = None) -> Optional[str]:
    if viewer is None:
        return mask_phone(phone)
    if viewer.id == owner_id or has_permission(viewer, Permission.PII_VIEW):
        return phone
    return mask_phone(phone)
