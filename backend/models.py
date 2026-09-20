import enum
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, JSON, Enum
)
from sqlalchemy.orm import relationship
from backend.database import Base

class UserRole(str, enum.Enum):
    FARMER = "FARMER"
    VETERINARIAN = "VETERINARIAN"
    PARA_VET = "PARA_VET"
    LAB_TECHNICIAN = "LAB_TECHNICIAN"
    LAB_ADMIN = "LAB_ADMIN"
    BLOCK_OFFICER = "BLOCK_OFFICER"
    DISTRICT_OFFICER = "DISTRICT_OFFICER"
    STATE_OFFICER = "STATE_OFFICER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(32), index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default=UserRole.FARMER.value, nullable=False)
    full_name = Column(String(255), nullable=False)
    
    # Geographic hierarchy
    state = Column(String(128), default="Maharashtra")
    division = Column(String(128), nullable=True)
    district = Column(String(128), nullable=True, index=True)
    taluka = Column(String(128), nullable=True)
    village = Column(String(128), nullable=True)
    
    # Professional fields for Veterinarian / Lab / Govt
    license_number = Column(String(128), nullable=True)
    qualification = Column(String(255), nullable=True)
    specialization = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)
    service_area = Column(String(255), nullable=True)
    designation = Column(String(128), nullable=True)
    department = Column(String(128), nullable=True)
    jurisdiction = Column(String(128), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True)
    refresh_token = Column(String(512), index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(64), primary_key=True, index=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    name = Column(String(255), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    total_area_acres = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Herd(Base):
    __tablename__ = "herds"

    id = Column(String(64), primary_key=True, index=True)
    farm_id = Column(String(64), ForeignKey("farms.id"), nullable=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    species = Column(String(64), nullable=False)
    total_animals = Column(Integer, default=1)
    health_status = Column(String(64), default="Healthy")
    risk_score = Column(Float, default=0.0)
    village = Column(String(128), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Animal(Base):
    __tablename__ = "animals"

    id = Column(String(64), primary_key=True, index=True)
    tag_id = Column(String(64), index=True, nullable=False)
    farm_id = Column(String(64), ForeignKey("farms.id"), nullable=True)
    herd_id = Column(String(64), ForeignKey("herds.id"), nullable=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    species = Column(String(64), nullable=False)
    breed = Column(String(128), nullable=True)
    sex = Column(String(16), default="Female")
    age_years = Column(Float, default=2.0)
    health_status = Column(String(64), default="Healthy")
    risk_score = Column(Float, default=0.0)
    village = Column(String(128), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DiseaseReport(Base):
    __tablename__ = "disease_reports"

    id = Column(String(64), primary_key=True, index=True)
    report_number = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True)
    reporter_name = Column(String(255), nullable=True)
    reporter_role = Column(String(32), default="FARMER")
    
    species = Column(String(64), nullable=False)
    number_affected = Column(Integer, default=1)
    number_dead = Column(Integer, default=0)
    symptoms = Column(JSON, default=list)
    temperature = Column(Float, nullable=True)
    
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    
    suspected_disease = Column(String(128), default="Unknown")
    status = Column(String(32), default="Suspected") # Suspected, Triaged, Investigating, Confirmed, Resolved
    
    # Triage Engine Output
    triage_urgency = Column(String(32), default="NORMAL") # ROUTINE, URGENT, EMERGENCY, CRITICAL
    triage_risk_level = Column(String(32), default="MODERATE") # LOW, MODERATE, HIGH, CRITICAL
    triage_recommendations = Column(JSON, default=list)
    
    notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False)
    source = Column(String(32), default="LIVE") # LIVE, DEMO, OFFLINE_SYNC
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VeterinaryCase(Base):
    __tablename__ = "veterinary_cases"

    id = Column(String(64), primary_key=True, index=True)
    case_number = Column(String(64), unique=True, index=True)
    report_id = Column(String(64), ForeignKey("disease_reports.id"), nullable=True, index=True)
    animal_id = Column(String(64), ForeignKey("animals.id"), nullable=True)
    herd_id = Column(String(64), ForeignKey("herds.id"), nullable=True)
    farmer_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    assigned_vet_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    
    # Workflow Status
    # REPORTED -> TRIAGED -> ASSIGNED -> ACCEPTED -> EN_ROUTE -> ON_SITE -> UNDER_EXAMINATION -> TREATMENT -> LAB_REQUIRED -> FOLLOW_UP -> RESOLVED -> CLOSED
    status = Column(String(64), default="REPORTED")
    priority = Column(String(32), default="HIGH") # LOW, MEDIUM, HIGH, CRITICAL
    
    species = Column(String(64), nullable=False)
    district = Column(String(128), nullable=False)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    
    reported_problem = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment_prescribed = Column(Text, nullable=True)
    risk_score = Column(Float, default=50.0)
    
    # Stage Timestamps
    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    en_route_at = Column(DateTime, nullable=True)
    on_site_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VeterinaryVisit(Base):
    __tablename__ = "veterinary_visits"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("veterinary_cases.id"), index=True)
    vet_id = Column(String(64), ForeignKey("users.id"))
    visit_date = Column(DateTime, default=datetime.utcnow)
    observations = Column(Text, nullable=True)
    treatment_given = Column(Text, nullable=True)
    follow_up_needed = Column(Boolean, default=False)
    follow_up_date = Column(DateTime, nullable=True)

class Laboratory(Base):
    __tablename__ = "laboratories"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(64), unique=True, index=True)
    district = Column(String(128), index=True, nullable=False)
    state = Column(String(128), default="Maharashtra")
    address = Column(String(255), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    contact_phone = Column(String(32), nullable=True)
    contact_email = Column(String(255), nullable=True)
    accreditation = Column(String(128), default="NABL Accredited")
    services = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)

class LabSample(Base):
    __tablename__ = "lab_samples"

    id = Column(String(64), primary_key=True, index=True)
    sample_code = Column(String(64), unique=True, index=True)
    case_id = Column(String(64), ForeignKey("veterinary_cases.id"), nullable=True, index=True)
    animal_id = Column(String(64), nullable=True)
    farmer_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    lab_id = Column(String(64), ForeignKey("laboratories.id"), nullable=True, index=True)
    collected_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    
    species = Column(String(64), nullable=False)
    disease_suspected = Column(String(128), nullable=False)
    sample_type = Column(String(64), nullable=False) # Blood, Serum, Nasal Swab, Tissue, Milk
    priority = Column(String(32), default="Routine") # Routine, Urgent, Critical
    
    # Sample Lifecycle: COLLECTED -> IN_TRANSIT -> RECEIVED -> ACCEPTED -> TESTING -> RESULT_PENDING -> VERIFIED -> RELEASED -> CLOSED
    status = Column(String(64), default="COLLECTED")
    
    collection_date = Column(DateTime, default=datetime.utcnow)
    received_at = Column(DateTime, nullable=True)
    tested_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    
    location = Column(String(128), nullable=True)
    district = Column(String(128), nullable=False)
    qr_code = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Verification details
    verified_by_id = Column(String(64), nullable=True)
    verified_by_name = Column(String(128), nullable=True)
    verification_remarks = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class LabTest(Base):
    __tablename__ = "lab_tests"

    id = Column(String(64), primary_key=True, index=True)
    sample_id = Column(String(64), ForeignKey("lab_samples.id"), index=True)
    test_name = Column(String(128), nullable=False) # RT-PCR, ELISA, Serology, Smear microscopy
    status = Column(String(32), default="Pending") # Pending, In Progress, Completed, Failed
    result = Column(String(32), nullable=True) # Positive, Negative, Inconclusive, Invalid
    value = Column(String(128), nullable=True)
    remarks = Column(Text, nullable=True)
    tested_by_id = Column(String(64), nullable=True)
    tested_at = Column(DateTime, nullable=True)

class VaccinationCampaign(Base):
    __tablename__ = "vaccination_campaigns"

    id = Column(String(64), primary_key=True, index=True)
    campaign_code = Column(String(64), unique=True, index=True)
    name = Column(String(255), nullable=False)
    disease = Column(String(128), nullable=False)
    vaccine = Column(String(128), nullable=False)
    species = Column(JSON, default=list)
    target_districts = Column(JSON, default=list)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(32), default="Active") # Draft, Planned, Active, Paused, Completed, Cancelled
    target_population = Column(Integer, default=100000)
    coverage_target_percent = Column(Float, default=85.0)
    current_vaccinated = Column(Integer, default=0)

class VaccinationRecord(Base):
    __tablename__ = "vaccination_records"

    id = Column(String(64), primary_key=True, index=True)
    animal_id = Column(String(64), nullable=False, index=True)
    herd_id = Column(String(64), nullable=True)
    species = Column(String(64), nullable=False)
    disease = Column(String(128), nullable=False)
    vaccine = Column(String(128), nullable=False)
    batch_number = Column(String(64), nullable=False)
    vaccination_date = Column(DateTime, default=datetime.utcnow)
    next_due_date = Column(DateTime, nullable=True)
    campaign_id = Column(String(64), ForeignKey("vaccination_campaigns.id"), nullable=True)
    provider_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    provider_name = Column(String(128), nullable=True)
    location = Column(String(128), nullable=True)
    district = Column(String(128), nullable=False)
    status = Column(String(32), default="Administered")

class OutbreakEvent(Base):
    __tablename__ = "outbreak_events"

    id = Column(String(64), primary_key=True, index=True)
    outbreak_code = Column(String(64), unique=True, index=True)
    disease = Column(String(128), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True)
    village = Column(String(128), nullable=True)
    center_lat = Column(Float, nullable=False)
    center_lng = Column(Float, nullable=False)
    radius_km = Column(Float, default=5.0)
    affected_count = Column(Integer, default=0)
    death_count = Column(Integer, default=0)
    status = Column(String(32), default="Active") # Active, Contained, Under Review, Resolved
    severity = Column(String(32), default="High") # Moderate, High, Critical
    date_detected = Column(DateTime, default=datetime.utcnow)
    date_contained = Column(DateTime, nullable=True)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, index=True)
    alert_code = Column(String(64), unique=True, index=True)
    type = Column(String(32), default="warning") # high, warning, success, info
    severity = Column(String(32), default="HIGH") # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    district = Column(String(128), nullable=True, index=True)
    taluka = Column(String(128), nullable=True)
    disease = Column(String(128), nullable=True)
    is_broadcast = Column(Boolean, default=False)
    target_roles = Column(JSON, default=list) # List of roles: ["FARMER", "VETERINARIAN", ...]
    read_by = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    channel = Column(String(32), default="IN_APP") # SMS, WHATSAPP, EMAIL, IN_APP
    template = Column(String(64), nullable=False) # HIGH_RISK_ALERT, VETERINARIAN_ASSIGNED, etc.
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(String(32), default="SENT") # PENDING, SENT, DELIVERED, FAILED
    delivery_details = Column(JSON, default=dict)
    sent_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    user_name = Column(String(128), nullable=True)
    role = Column(String(32), nullable=True)
    action = Column(String(64), nullable=False) # CASE_CREATED, LAB_RESULT_VERIFIED, etc.
    resource = Column(String(64), nullable=False) # CASE, SAMPLE, REPORT, USER, CONFIG
    resource_id = Column(String(64), nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ExternalDataRecord(Base):
    __tablename__ = "external_data_records"

    id = Column(String(64), primary_key=True, index=True)
    provider = Column(String(64), nullable=False) # NADRES, DAHD_CENSUS, WEATHER, SURVEILLANCE
    external_id = Column(String(128), nullable=True)
    source = Column(String(128), nullable=False)
    record_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    data_status = Column(String(32), default="LIVE") # LIVE, DEMO, HISTORICAL, UNAVAILABLE
    confidence = Column(Float, default=1.0)
    retrieved_at = Column(DateTime, default=datetime.utcnow)

class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    client_sync_id = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    operation = Column(String(32), nullable=False) # CREATE, UPDATE, DELETE
    status = Column(String(32), default="PROCESSED") # PROCESSED, CONFLICT, FAILED
    processed_at = Column(DateTime, default=datetime.utcnow)
