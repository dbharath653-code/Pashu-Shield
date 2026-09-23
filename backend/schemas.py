"""Request/response schemas with strict validation. Field names are preserved for API compatibility."""
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

PHONE_RE = re.compile(r"^\+?[0-9]{10,13}$")
ID_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")
SAMPLE_CODE_RE = re.compile(r"^[A-Z0-9\-]{4,64}$")

Name = Field(min_length=1, max_length=255)
Place = Field(min_length=1, max_length=128)


def _phone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    v = re.sub(r"[\s\-()]", "", v)
    if not PHONE_RE.match(v):
        raise ValueError("phone must be 10–13 digits, optionally prefixed with +")
    return v


def _not_future(v: Optional[datetime]) -> Optional[datetime]:
    if v is not None and v.replace(tzinfo=None) > datetime.utcnow() + timedelta(minutes=10):
        raise ValueError("timestamp cannot be in the future")
    if v is not None and v.year < 2000:
        raise ValueError("timestamp is implausibly old")
    return v


class _Coords(BaseModel):
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def _pair(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat and lng must be provided together")
        if self.lat == 0 and self.lng == 0:
            raise ValueError("(0,0) is not a valid field location")
        return self


# --- Auth & User ---------------------------------------------------------------------------
class FarmerRegister(BaseModel):
    full_name: str = Name
    phone: str
    email: Optional[EmailStr] = None
    password: str = Field(min_length=1, max_length=128)
    district: str = Place
    taluka: Optional[str] = Field(default=None, max_length=128)
    village: str = Place
    notification_language: Optional[str] = Field(default="en", max_length=8)
    sms_opt_in: bool = False
    whatsapp_opt_in: bool = False
    _p = field_validator("phone")(classmethod(lambda cls, v: _phone(v)))


class VetRegister(BaseModel):
    full_name: str = Name
    email: EmailStr
    phone: str
    password: str = Field(min_length=1, max_length=128)
    license_number: str = Field(min_length=3, max_length=128)
    qualification: str = Field(min_length=2, max_length=255)
    specialization: Optional[str] = Field(default=None, max_length=255)
    organization: Optional[str] = Field(default=None, max_length=255)
    district: str = Place
    taluka: Optional[str] = Field(default=None, max_length=128)
    service_area: Optional[str] = Field(default=None, max_length=255)
    _p = field_validator("phone")(classmethod(lambda cls, v: _phone(v)))


class LabRegister(BaseModel):
    lab_name: str = Name
    email: EmailStr
    phone: str
    password: str = Field(min_length=1, max_length=128)
    accreditation: Optional[str] = Field(default=None, max_length=128)
    district: str = Place
    address: Optional[str] = Field(default=None, max_length=255)
    services: Optional[List[str]] = []
    _p = field_validator("phone")(classmethod(lambda cls, v: _phone(v)))


class GovernmentRegister(BaseModel):
    full_name: str = Name
    email: EmailStr
    phone: str
    password: str = Field(min_length=1, max_length=128)
    department: Optional[str] = Field(default=None, max_length=128)
    designation: Optional[str] = Field(default=None, max_length=128)
    jurisdiction: Optional[str] = Field(default=None, max_length=128)
    district: Optional[str] = Field(default=None, max_length=128)
    taluka: Optional[str] = Field(default=None, max_length=128)
    # Requested role; self-signup can never grant SYSTEM_ADMIN and always needs approval.
    role: Optional[str] = "DISTRICT_OFFICER"
    _p = field_validator("phone")(classmethod(lambda cls, v: _phone(v)))


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    device_id: Optional[str] = Field(default=None, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: Dict[str, Any]


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    phone: Optional[str]
    full_name: str
    role: str
    district: Optional[str]
    taluka: Optional[str]
    village: Optional[str]
    license_number: Optional[str]
    qualification: Optional[str]
    organization: Optional[str]
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None
    created_at: datetime


# --- Animals & Herds -----------------------------------------------------------------------
class FarmCreate(_Coords):
    name: str = Name
    district: str = Place
    taluka: Optional[str] = None
    village: str = Place
    total_area_acres: Optional[float] = Field(default=None, ge=0, le=100000)


class AnimalCreate(_Coords):
    tag_id: str = Field(min_length=1, max_length=64)
    species: str = Field(min_length=1, max_length=64)
    breed: Optional[str] = Field(default=None, max_length=128)
    sex: str = Field(default="Female", max_length=16)
    age_years: Optional[float] = Field(default=None, ge=0, le=40)
    village: str = Place
    district: str = Place
    taluka: Optional[str] = Field(default=None, max_length=128)
    herd_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    farm_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)


class HerdCreate(_Coords):
    species: str = Field(min_length=1, max_length=64)
    total_animals: int = Field(default=1, ge=1, le=100000)
    village: str = Place
    district: str = Place
    taluka: Optional[str] = Field(default=None, max_length=128)
    farm_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)


# --- Disease Reports & Triage ---------------------------------------------------------------
class DiseaseReportCreate(_Coords):
    species: str = Field(min_length=1, max_length=64)
    number_affected: int = Field(default=1, ge=0, le=100000)
    number_dead: int = Field(default=0, ge=0, le=100000)
    symptoms: List[str] = Field(default_factory=list, max_length=40)
    temperature: Optional[float] = None
    temperature_unit: Optional[Literal["C", "F"]] = None
    district: str = Place
    taluka: Optional[str] = Field(default=None, max_length=128)
    village: str = Place
    location_source: Optional[Literal["GPS", "USER_ENTERED"]] = None
    suspected_disease: Optional[str] = Field(default="Unknown", max_length=128)
    notes: Optional[str] = Field(default=None, max_length=4000)
    idempotency_key: Optional[str] = Field(default=None, max_length=128)
    client_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    # Capture channel chosen by the client. Server-controlled channels (DEMO/OFFLINE_SYNC/IVR) cannot be claimed.
    channel: Optional[Literal["APP", "VOICE"]] = None
    observed_at: Optional[datetime] = None
    _t = field_validator("observed_at")(classmethod(lambda cls, v: _not_future(v)))

    @field_validator("symptoms")
    @classmethod
    def _sym(cls, v: List[str]) -> List[str]:
        return [s.strip()[:120] for s in v if s and s.strip()]


class ReportVerifyRequest(BaseModel):
    verification_status: Literal["VERIFIED", "REJECTED"]
    confirmed_disease: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=2000)


# --- Veterinary Cases & Dispatch ----------------------------------------------------------
class CaseStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=64)
    diagnosis: Optional[str] = Field(default=None, max_length=4000)
    treatment_prescribed: Optional[str] = Field(default=None, max_length=4000)
    notes: Optional[str] = Field(default=None, max_length=4000)
    expected_version: Optional[int] = None


class CaseAssignRequest(BaseModel):
    vet_id: str = Field(pattern=ID_RE.pattern)


class DispatchResponse(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=1000)


class VetLocationUpdate(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: Optional[float] = Field(default=None, ge=0, le=100000)


class VetProfileUpdate(BaseModel):
    availability_status: Optional[Literal["AVAILABLE", "BUSY", "OFF_DUTY"]] = None
    service_radius_km: Optional[float] = Field(default=None, gt=0, le=300)
    specializations: Optional[List[str]] = None
    working_hours: Optional[Dict[str, List[str]]] = None
    has_transport: Optional[bool] = None
    max_active_cases: Optional[int] = Field(default=None, ge=1, le=50)


class VisitCreate(BaseModel):
    observations: str = Field(min_length=1, max_length=8000)
    treatment_given: str = Field(default="", max_length=8000)
    follow_up_needed: bool = False
    follow_up_date: Optional[datetime] = None
    request_sample: bool = False


# --- Lab Management -----------------------------------------------------------------------
class SampleCreate(BaseModel):
    case_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    animal_id: Optional[str] = Field(default=None, max_length=64)
    species: str = Field(min_length=1, max_length=64)
    disease_suspected: str = Field(min_length=1, max_length=128)
    sample_type: str = Field(min_length=1, max_length=64)
    priority: str = Field(default="Routine", max_length=32)
    district: str = Place
    location: Optional[str] = Field(default=None, max_length=128)
    lab_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    notes: Optional[str] = Field(default=None, max_length=4000)
    tests: List[str] = Field(default_factory=lambda: ["RT-PCR"], max_length=20)
    id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)


class SampleStatusUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=64)
    notes: Optional[str] = Field(default=None, max_length=4000)
    condition: Optional[str] = Field(default=None, max_length=64)
    transfer_to: Optional[str] = Field(default=None, max_length=128)
    temperature_c: Optional[float] = Field(default=None, ge=-80, le=60)
    rejection_reason: Optional[str] = Field(default=None, max_length=2000)


class CustodyEventCreate(BaseModel):
    event_type: Literal["HANDOVER", "IN_TRANSIT", "RECEIVED", "STORAGE", "CONDITION_CHECK"]
    transfer_from: Optional[str] = Field(default=None, max_length=128)
    transfer_to: Optional[str] = Field(default=None, max_length=128)
    condition: Optional[str] = Field(default=None, max_length=64)
    transport_status: Optional[str] = Field(default=None, max_length=64)
    temperature_c: Optional[float] = Field(default=None, ge=-80, le=60)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    location_label: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=2000)
    occurred_at: Optional[datetime] = None
    _t = field_validator("occurred_at")(classmethod(lambda cls, v: _not_future(v)))


class TestResultUpdate(BaseModel):
    test_id: str = Field(pattern=ID_RE.pattern)
    status: Literal["Pending", "In Progress", "Completed", "Failed"]
    result: Literal["Positive", "Negative", "Inconclusive", "Invalid"]
    value: Optional[str] = Field(default=None, max_length=128)
    remarks: Optional[str] = Field(default=None, max_length=4000)
    correction_reason: Optional[str] = Field(default=None, max_length=2000)


class SampleVerificationRequest(BaseModel):
    remarks: str = Field(min_length=1, max_length=4000)
    final_result: Optional[Literal["POSITIVE", "NEGATIVE", "INCONCLUSIVE"]] = None


# --- Vaccinations ---------------------------------------------------------------------------
class CampaignCreate(BaseModel):
    name: str = Name
    disease: str = Field(min_length=1, max_length=128)
    vaccine: str = Field(min_length=1, max_length=128)
    species: List[str]
    target_districts: List[str]
    start_date: datetime
    end_date: datetime
    target_population: int = Field(default=100000, ge=1)
    coverage_target_percent: float = Field(default=85.0, gt=0, le=100)

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class VaccinationRecordCreate(_Coords):
    animal_id: str = Field(min_length=1, max_length=64)
    herd_id: Optional[str] = Field(default=None, max_length=64)
    species: str = Field(min_length=1, max_length=64)
    disease: str = Field(min_length=1, max_length=128)
    vaccine: str = Field(min_length=1, max_length=128)
    manufacturer: Optional[str] = Field(default=None, max_length=128)
    batch_number: str = Field(min_length=1, max_length=64)
    dose_number: int = Field(default=1, ge=1, le=10)
    vaccination_date: Optional[datetime] = None
    next_due_date: Optional[datetime] = None
    district: str = Place
    location: Optional[str] = Field(default=None, max_length=128)
    campaign_id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    adverse_event: Optional[str] = Field(default=None, max_length=2000)
    id: Optional[str] = Field(default=None, pattern=ID_RE.pattern)
    _t = field_validator("vaccination_date")(classmethod(lambda cls, v: _not_future(v)))


# --- Offline Sync ---------------------------------------------------------------------------
class SyncItemSchema(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    store: str = Field(min_length=1, max_length=64)
    id: str = Field(min_length=1, max_length=128)
    operation: Literal["CREATE", "UPDATE", "DELETE"] = "CREATE"
    data: Dict[str, Any]
    base_version: Optional[int] = None
    client_updated_at: Optional[datetime] = None
    device_id: Optional[str] = Field(default=None, max_length=128)
    sequence: Optional[int] = None


class SyncPushRequest(BaseModel):
    items: List[SyncItemSchema] = Field(max_length=200)
    device_id: Optional[str] = Field(default=None, max_length=128)


class ConflictResolution(BaseModel):
    resolution: Literal["KEEP_SERVER", "KEEP_CLIENT", "MERGED"]
    merged_data: Optional[Dict[str, Any]] = None


# --- Voice & Intents ------------------------------------------------------------------------
class VoiceIntentRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", max_length=8)
    current_location: Optional[Dict[str, Any]] = None


class VoiceIntentResponse(BaseModel):
    intent: str
    entities: Dict[str, Any]
    fulfillment_text: str
    requires_confirmation: bool
    action_payload: Optional[Dict[str, Any]] = None
    next_step: Optional[str] = None
    confidence: Optional[float] = None
    engine: Optional[str] = None
    validation_errors: Optional[List[str]] = None
