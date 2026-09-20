from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

# --- Auth & User ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = "FARMER"
    district: Optional[str] = None
    taluka: Optional[str] = None
    village: Optional[str] = None

class FarmerRegister(BaseModel):
    full_name: str
    phone: str
    email: Optional[EmailStr] = None
    password: str
    district: str
    taluka: Optional[str] = None
    village: str

class VetRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    license_number: str
    qualification: str
    specialization: Optional[str] = None
    organization: Optional[str] = None
    district: str
    taluka: Optional[str] = None
    service_area: Optional[str] = None

class LabRegister(BaseModel):
    lab_name: str
    email: EmailStr
    phone: str
    password: str
    accreditation: Optional[str] = "NABL Accredited"
    district: str
    address: Optional[str] = None
    services: Optional[List[str]] = []

class GovernmentRegister(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str
    department: Optional[str] = "Department of Animal Husbandry, Govt. of Maharashtra"
    designation: Optional[str] = "Surveillance Officer"
    jurisdiction: Optional[str] = "Maharashtra State"
    district: Optional[str] = "Pune"
    role: Optional[str] = "STATE_OFFICER"

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserProfile(BaseModel):
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
    created_at: datetime

# --- Animals & Herds ---
class FarmCreate(BaseModel):
    name: str
    district: str
    taluka: Optional[str] = None
    village: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    total_area_acres: Optional[float] = None

class AnimalCreate(BaseModel):
    tag_id: str
    species: str
    breed: Optional[str] = None
    sex: str = "Female"
    age_years: float = 2.0
    village: str
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    herd_id: Optional[str] = None
    farm_id: Optional[str] = None

class HerdCreate(BaseModel):
    species: str
    total_animals: int = 1
    village: str
    district: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    farm_id: Optional[str] = None

# --- Disease Reports & Triage ---
class DiseaseReportCreate(BaseModel):
    species: str
    number_affected: int = 1
    number_dead: int = 0
    symptoms: List[str] = []
    temperature: Optional[float] = None
    district: str
    taluka: Optional[str] = None
    village: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    suspected_disease: Optional[str] = "Unknown"
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None

class TriageResult(BaseModel):
    risk_level: str
    urgency: str
    confidence: float
    recommended_actions: List[str]
    requires_veterinary_dispatch: bool
    requires_lab_sampling: bool
    biosecurity_instructions: List[str]

# --- Veterinary Cases & Dispatch ---
class CaseStatusUpdate(BaseModel):
    status: str
    diagnosis: Optional[str] = None
    treatment_prescribed: Optional[str] = None
    notes: Optional[str] = None

class CaseAssignRequest(BaseModel):
    case_id: str
    vet_id: str

class VisitCreate(BaseModel):
    observations: str
    treatment_given: str
    follow_up_needed: bool = False
    follow_up_date: Optional[datetime] = None

# --- Lab Management ---
class SampleCreate(BaseModel):
    case_id: Optional[str] = None
    animal_id: Optional[str] = None
    species: str
    disease_suspected: str
    sample_type: str
    priority: str = "Routine"
    district: str
    location: Optional[str] = None
    notes: Optional[str] = None
    tests: List[str] = ["RT-PCR"]

class SampleStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class TestResultUpdate(BaseModel):
    test_id: str
    status: str
    result: str # Positive, Negative, Inconclusive
    value: Optional[str] = None
    remarks: Optional[str] = None

class SampleVerificationRequest(BaseModel):
    remarks: str

# --- Vaccinations ---
class CampaignCreate(BaseModel):
    name: str
    disease: str
    vaccine: str
    species: List[str]
    target_districts: List[str]
    start_date: datetime
    end_date: datetime
    target_population: int = 100000
    coverage_target_percent: float = 85.0

class VaccinationRecordCreate(BaseModel):
    animal_id: str
    species: str
    disease: str
    vaccine: str
    batch_number: str
    vaccination_date: Optional[datetime] = None
    next_due_date: Optional[datetime] = None
    district: str
    location: Optional[str] = None
    campaign_id: Optional[str] = None

# --- Offline Sync ---
class SyncItemSchema(BaseModel):
    idempotency_key: str
    store: str
    id: str
    operation: str # CREATE, UPDATE, DELETE
    data: Dict[str, Any]

class SyncPushRequest(BaseModel):
    items: List[SyncItemSchema]

# --- Voice & Intents ---
class VoiceIntentRequest(BaseModel):
    transcript: str
    language: str = "en"
    current_location: Optional[Dict[str, Any]] = None

class VoiceIntentResponse(BaseModel):
    intent: str
    entities: Dict[str, Any]
    fulfillment_text: str
    requires_confirmation: bool
    action_payload: Optional[Dict[str, Any]] = None
    next_step: Optional[str] = None
