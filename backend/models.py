"""
SQLAlchemy models for Pashu-Shield.

Conventions
-----------
* All existing columns/API field names are preserved; new columns are additive.
* Synchronised entities carry `version`, `updated_at`, `updated_by`, `device_id` (optimistic
  concurrency + deterministic conflict detection) and `deleted_at` (soft delete).
* Records created by the demo seed carry `is_demo = True` and are excluded from surveillance
  analytics when DATA_MODE=live.
* Spatial data: lat/lng float columns are the portable source of truth. On PostgreSQL the
  Alembic migration `0002_postgis` adds generated `geog geography(Point,4326)` columns with GiST
  indexes, used by services/spatial.py for ST_DWithin / ST_Distance queries.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint,
)

from backend.database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


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


class SyncMixin:
    """Columns required on every offline-synchronised entity."""
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, index=True)
    updated_by = Column(String(64), nullable=True)
    device_id = Column(String(128), nullable=True)
    deleted_at = Column(DateTime, nullable=True)


# ----------------------------------------------------------------------------------------
# Identity & access
# ----------------------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(32), index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default=UserRole.FARMER.value, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)

    state = Column(String(128), default="Maharashtra")
    division = Column(String(128), nullable=True)
    district = Column(String(128), nullable=True, index=True)
    taluka = Column(String(128), nullable=True, index=True)  # taluka == block
    village = Column(String(128), nullable=True)

    license_number = Column(String(128), nullable=True)
    qualification = Column(String(255), nullable=True)
    specialization = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)
    service_area = Column(String(255), nullable=True)
    designation = Column(String(128), nullable=True)
    department = Column(String(128), nullable=True)
    jurisdiction = Column(String(128), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    # Self-registered professional/government accounts start unverified and must be approved.
    is_verified = Column(Boolean, default=False, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False)
    failed_login_count = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    notification_language = Column(String(8), default="en")
    sms_opt_in = Column(Boolean, default=False, nullable=False)
    whatsapp_opt_in = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class UserSession(Base):
    """One row per issued refresh token. Rotation creates a new row in the same family."""
    __tablename__ = "user_sessions"

    id = Column(String(64), primary_key=True)  # == refresh token jti
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    family_id = Column(String(64), index=True, nullable=False)
    refresh_token_hash = Column(String(128), index=True, nullable=False)  # sha256, never the raw token
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_reason = Column(String(64), nullable=True)
    replaced_by = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(64), nullable=True)
    device_id = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    last_used_at = Column(DateTime, nullable=True)


# ----------------------------------------------------------------------------------------
# Farms, herds, animals
# ----------------------------------------------------------------------------------------
class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(64), primary_key=True, index=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    name = Column(String(255), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True, index=True)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    total_area_acres = Column(Float, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Herd(SyncMixin, Base):
    __tablename__ = "herds"

    id = Column(String(64), primary_key=True, index=True)
    farm_id = Column(String(64), ForeignKey("farms.id"), nullable=True, index=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    species = Column(String(64), nullable=False)
    total_animals = Column(Integer, default=1)
    health_status = Column(String(64), default="Healthy")
    risk_score = Column(Float, default=0.0)
    village = Column(String(128), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, index=True)


class Animal(SyncMixin, Base):
    __tablename__ = "animals"
    __table_args__ = (
        UniqueConstraint("owner_id", "tag_id", name="uq_animals_owner_tag"),
    )

    id = Column(String(64), primary_key=True, index=True)
    tag_id = Column(String(64), index=True, nullable=False)
    farm_id = Column(String(64), ForeignKey("farms.id"), nullable=True, index=True)
    herd_id = Column(String(64), ForeignKey("herds.id"), nullable=True, index=True)
    owner_id = Column(String(64), ForeignKey("users.id"), index=True)
    species = Column(String(64), nullable=False)
    breed = Column(String(128), nullable=True)
    sex = Column(String(16), default="Female")
    age_years = Column(Float, nullable=True)
    health_status = Column(String(64), default="Healthy")
    risk_score = Column(Float, default=0.0)
    village = Column(String(128), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, index=True)


# ----------------------------------------------------------------------------------------
# Disease reporting workflow
# ----------------------------------------------------------------------------------------
class DiseaseReport(SyncMixin, Base):
    __tablename__ = "disease_reports"
    __table_args__ = (
        CheckConstraint("number_affected >= 0", name="ck_reports_affected_nonneg"),
        CheckConstraint("number_dead >= 0", name="ck_reports_dead_nonneg"),
        Index("ix_reports_district_status_created", "district", "status", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    report_number = Column(String(64), unique=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), index=True, nullable=True)
    reporter_name = Column(String(255), nullable=True)
    reporter_role = Column(String(32), default="FARMER")

    species = Column(String(64), nullable=False, index=True)
    number_affected = Column(Integer, default=1, nullable=False)
    number_dead = Column(Integer, default=0, nullable=False)
    symptoms = Column(JSON, default=list)
    # Canonical storage unit is degrees Celsius. `temperature` is kept for API compatibility and
    # always mirrors temperature_c.
    temperature = Column(Float, nullable=True)
    temperature_c = Column(Float, nullable=True)
    temperature_unit_reported = Column(String(1), nullable=True)  # "C" | "F"

    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True, index=True)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    # GPS | USER_ENTERED | LOCATION_UNAVAILABLE. Coordinates are never defaulted.
    location_status = Column(String(32), default="LOCATION_UNAVAILABLE", nullable=False)

    suspected_disease = Column(String(128), default="Unknown", index=True)
    # Workflow state (see services/workflow.py REPORT_TRANSITIONS)
    status = Column(String(32), default="SUBMITTED", index=True)

    triage_urgency = Column(String(32), default="ROUTINE")
    triage_risk_level = Column(String(32), default="MODERATE", index=True)
    triage_recommendations = Column(JSON, default=list)
    triage_confidence = Column(Float, nullable=True)
    triage_rule_version = Column(String(32), nullable=True)
    triage_explanation = Column(JSON, default=list)

    # Provenance (section 20)
    source_type = Column(String(32), default="FARMER_REPORT", nullable=False)
    verification_status = Column(String(32), default="UNVERIFIED", nullable=False, index=True)
    verified_by_id = Column(String(64), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False, index=True)
    source = Column(String(32), default="LIVE")  # LIVE, DEMO, OFFLINE_SYNC, IVR, VOICE
    client_id = Column(String(64), nullable=True, index=True)  # offline-created local id
    created_at = Column(DateTime, default=utcnow, index=True)
    reported_at = Column(DateTime, default=utcnow, index=True)


class VeterinaryCase(SyncMixin, Base):
    __tablename__ = "veterinary_cases"

    id = Column(String(64), primary_key=True, index=True)
    case_number = Column(String(64), unique=True, index=True)
    report_id = Column(String(64), ForeignKey("disease_reports.id"), nullable=True, index=True)
    animal_id = Column(String(64), ForeignKey("animals.id"), nullable=True)
    herd_id = Column(String(64), ForeignKey("herds.id"), nullable=True)
    farmer_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    assigned_vet_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)

    # See services/workflow.py CASE_TRANSITIONS
    status = Column(String(64), default="REPORTED", index=True)
    priority = Column(String(32), default="HIGH", index=True)

    species = Column(String(64), nullable=False)
    district = Column(String(128), nullable=False, index=True)
    taluka = Column(String(128), nullable=True, index=True)
    village = Column(String(128), nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    reported_problem = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=True)
    treatment_prescribed = Column(Text, nullable=True)
    risk_score = Column(Float, default=50.0)
    requires_lab = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False, nullable=False)

    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    en_route_at = Column(DateTime, nullable=True)
    on_site_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)


class WorkflowEvent(Base):
    """Append-only record of every state transition (reports, cases, samples, dispatch)."""
    __tablename__ = "workflow_events"

    id = Column(String(64), primary_key=True)
    entity_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    from_status = Column(String(64), nullable=True)
    to_status = Column(String(64), nullable=False)
    actor_id = Column(String(64), nullable=True)
    actor_role = Column(String(32), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, index=True)


class VeterinarianProfile(Base):
    """Operational dispatch data for veterinarians / para-vets. Location is never defaulted."""
    __tablename__ = "veterinarian_profiles"

    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    availability_status = Column(String(32), default="OFF_DUTY", nullable=False, index=True)  # AVAILABLE | BUSY | OFF_DUTY
    current_lat = Column(Float, nullable=True)
    current_lng = Column(Float, nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    location_accuracy_m = Column(Float, nullable=True)
    working_hours = Column(JSON, default=dict)  # {"mon": ["09:00","17:00"], ...}
    specializations = Column(JSON, default=list)  # species / disease competencies
    service_radius_km = Column(Float, default=40.0, nullable=False)
    has_transport = Column(Boolean, default=False, nullable=False)
    max_active_cases = Column(Integer, default=8, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class DispatchRequest(Base):
    __tablename__ = "dispatch_requests"
    __table_args__ = (Index("ix_dispatch_case_status", "case_id", "status"),)

    id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("veterinary_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    vet_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING | ACCEPTED | REJECTED | EXPIRED | CANCELLED
    rank = Column(Integer, default=1)
    distance_km = Column(Float, nullable=True)
    distance_basis = Column(String(32), nullable=True)  # STRAIGHT_LINE | ROAD | LOCATION_UNAVAILABLE
    eta_minutes = Column(Float, nullable=True)
    eta_status = Column(String(32), default="ETA_UNAVAILABLE")
    score_breakdown = Column(JSON, default=dict)
    reject_reason = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class VeterinaryVisit(Base):
    __tablename__ = "veterinary_visits"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("veterinary_cases.id"), index=True)
    vet_id = Column(String(64), ForeignKey("users.id"))
    visit_date = Column(DateTime, default=utcnow)
    observations = Column(Text, nullable=True)
    treatment_given = Column(Text, nullable=True)
    follow_up_needed = Column(Boolean, default=False)
    follow_up_date = Column(DateTime, nullable=True)


# ----------------------------------------------------------------------------------------
# Laboratory
# ----------------------------------------------------------------------------------------
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
    accreditation = Column(String(128), nullable=True)
    services = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    source = Column(String(64), default="ADMIN_ENTERED")


class VeterinaryFacility(Base):
    __tablename__ = "veterinary_facilities"

    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    facility_type = Column(String(64), nullable=False)
    district = Column(String(128), index=True, nullable=False)
    taluka = Column(String(128), nullable=True, index=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    mvu_available = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    source = Column(String(64), default="ADMIN_ENTERED")
    created_at = Column(DateTime, default=utcnow)


class LabSample(SyncMixin, Base):
    __tablename__ = "lab_samples"

    id = Column(String(64), primary_key=True, index=True)
    sample_code = Column(String(64), unique=True, index=True)
    case_id = Column(String(64), ForeignKey("veterinary_cases.id"), nullable=True, index=True)
    animal_id = Column(String(64), nullable=True)
    farmer_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    lab_id = Column(String(64), ForeignKey("laboratories.id"), nullable=True, index=True)
    collected_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)

    species = Column(String(64), nullable=False)
    disease_suspected = Column(String(128), nullable=False, index=True)
    sample_type = Column(String(64), nullable=False)
    priority = Column(String(32), default="Routine")

    # See services/workflow.py SAMPLE_TRANSITIONS
    status = Column(String(64), default="COLLECTED", index=True)

    collection_date = Column(DateTime, default=utcnow)
    received_at = Column(DateTime, nullable=True)
    tested_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)

    location = Column(String(128), nullable=True)
    district = Column(String(128), nullable=False, index=True)
    collection_lat = Column(Float, nullable=True)
    collection_lng = Column(Float, nullable=True)
    qr_code = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)

    verified_by_id = Column(String(64), nullable=True)
    verified_by_name = Column(String(128), nullable=True)
    verification_remarks = Column(Text, nullable=True)
    final_result = Column(String(32), nullable=True)  # POSITIVE | NEGATIVE | INCONCLUSIVE
    rejection_reason = Column(Text, nullable=True)
    external_lims_id = Column(String(128), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=utcnow, index=True)


class CustodyEvent(Base):
    """Immutable chain-of-custody log for a sample."""
    __tablename__ = "custody_events"

    id = Column(String(64), primary_key=True)
    sample_id = Column(String(64), ForeignKey("lab_samples.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type = Column(String(32), nullable=False)  # COLLECTED | HANDOVER | IN_TRANSIT | RECEIVED | REJECTED | ...
    actor_id = Column(String(64), nullable=True)
    transfer_from = Column(String(128), nullable=True)
    transfer_to = Column(String(128), nullable=True)
    condition = Column(String(64), nullable=True)  # GOOD | LEAKED | WARM | HAEMOLYSED ...
    transport_status = Column(String(64), nullable=True)
    temperature_c = Column(Float, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    location_label = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utcnow, nullable=False)
    recorded_at = Column(DateTime, default=utcnow, nullable=False)


class LabTest(Base):
    __tablename__ = "lab_tests"

    id = Column(String(64), primary_key=True, index=True)
    sample_id = Column(String(64), ForeignKey("lab_samples.id"), index=True)
    test_name = Column(String(128), nullable=False)
    status = Column(String(32), default="Pending")
    result = Column(String(32), nullable=True)
    value = Column(String(128), nullable=True)
    remarks = Column(Text, nullable=True)
    tested_by_id = Column(String(64), nullable=True)
    tested_at = Column(DateTime, nullable=True)
    result_version = Column(Integer, default=0, nullable=False)


class LabResultRevision(Base):
    """Every result entry/correction is versioned; earlier values are never overwritten silently."""
    __tablename__ = "lab_result_revisions"

    id = Column(String(64), primary_key=True)
    test_id = Column(String(64), ForeignKey("lab_tests.id", ondelete="CASCADE"), index=True, nullable=False)
    version = Column(Integer, nullable=False)
    result = Column(String(32), nullable=True)
    value = Column(String(128), nullable=True)
    remarks = Column(Text, nullable=True)
    entered_by_id = Column(String(64), nullable=True)
    correction_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


# ----------------------------------------------------------------------------------------
# Vaccination
# ----------------------------------------------------------------------------------------
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
    status = Column(String(32), default="Active")
    target_population = Column(Integer, default=100000)
    coverage_target_percent = Column(Float, default=85.0)
    current_vaccinated = Column(Integer, default=0)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(64), nullable=True)


class VaccinationRecord(SyncMixin, Base):
    __tablename__ = "vaccination_records"
    __table_args__ = (
        UniqueConstraint("animal_id", "disease", "dose_number", "vaccination_day", name="uq_vacc_animal_disease_dose_day"),
    )

    id = Column(String(64), primary_key=True, index=True)
    animal_id = Column(String(64), nullable=False, index=True)
    herd_id = Column(String(64), nullable=True)
    species = Column(String(64), nullable=False)
    disease = Column(String(128), nullable=False)
    vaccine = Column(String(128), nullable=False)
    manufacturer = Column(String(128), nullable=True)
    batch_number = Column(String(64), nullable=False)
    dose_number = Column(Integer, default=1, nullable=False)
    vaccination_date = Column(DateTime, default=utcnow, index=True)
    vaccination_day = Column(String(10), nullable=False)  # YYYY-MM-DD, used for duplicate prevention
    next_due_date = Column(DateTime, nullable=True, index=True)
    campaign_id = Column(String(64), ForeignKey("vaccination_campaigns.id"), nullable=True)
    provider_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    provider_name = Column(String(128), nullable=True)
    location = Column(String(128), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    district = Column(String(128), nullable=False, index=True)
    status = Column(String(32), default="Administered")
    adverse_event = Column(Text, nullable=True)
    reminder_sent_at = Column(DateTime, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)


# ----------------------------------------------------------------------------------------
# Surveillance, outbreaks, alerts, notifications
# ----------------------------------------------------------------------------------------
class SurveillanceObservation(Base):
    """Normalised surveillance record from any source, always carrying provenance."""
    __tablename__ = "surveillance_observations"
    __table_args__ = (
        UniqueConstraint("source_name", "source_record_id", name="uq_obs_source_record"),
        Index("ix_obs_district_disease_observed", "district", "disease", "observed_at"),
    )

    id = Column(String(64), primary_key=True)
    disease = Column(String(128), nullable=False, index=True)
    species = Column(String(64), nullable=True)
    district = Column(String(128), nullable=True, index=True)
    block = Column(String(128), nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    case_count = Column(Integer, default=0, nullable=False)
    death_count = Column(Integer, default=0, nullable=False)
    observed_at = Column(DateTime, nullable=False, index=True)
    retrieved_at = Column(DateTime, default=utcnow, nullable=False)
    source_type = Column(String(32), nullable=False)  # GOVERNMENT | FARMER_REPORT | VETERINARY_REPORT | LAB | DEMO
    source_name = Column(String(64), nullable=False)
    source_record_id = Column(String(128), nullable=False)
    request_id = Column(String(64), nullable=True)
    data_version = Column(String(32), nullable=True)
    raw_reference = Column(String(255), nullable=True)
    verification_status = Column(String(32), default="UNVERIFIED", nullable=False)
    confidence = Column(Float, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)


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
    status = Column(String(32), default="Active")
    severity = Column(String(32), default="High")
    # REPORTED | UNDER_VERIFICATION | VETERINARIAN_VERIFIED | LAB_CONFIRMED | PREDICTED_RISK
    evidence_level = Column(String(32), default="REPORTED")
    evidence = Column(JSON, default=dict)
    detection_method = Column(String(64), default="MANUAL")
    is_demo = Column(Boolean, default=False, nullable=False)
    date_detected = Column(DateTime, default=utcnow)
    date_contained = Column(DateTime, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, index=True)
    alert_code = Column(String(64), unique=True, index=True)
    alert_type = Column(String(32), default="HIGH_RISK_REPORT", index=True)
    type = Column(String(32), default="warning")  # UI style: high, warning, success, info
    severity = Column(String(32), default="HIGH", index=True)  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    district = Column(String(128), nullable=True, index=True)
    taluka = Column(String(128), nullable=True)
    disease = Column(String(128), nullable=True)
    is_broadcast = Column(Boolean, default=False)
    target_roles = Column(JSON, default=list)
    read_by = Column(JSON, default=list)
    dedup_key = Column(String(191), unique=True, nullable=True)
    related_entity_type = Column(String(32), nullable=True)
    related_entity_id = Column(String(64), nullable=True)
    evidence_level = Column(String(32), default="REPORTED")
    occurrences = Column(Integer, default=1, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, index=True)
    last_occurred_at = Column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id"), nullable=True, index=True)
    channel = Column(String(32), default="IN_APP")
    template = Column(String(64), nullable=False)
    language = Column(String(8), default="en")
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    # QUEUED -> SUBMITTED -> SENT -> DELIVERED -> READ | FAILED | NOT_CONFIGURED | SUPPRESSED
    status = Column(String(32), default="QUEUED", index=True)
    provider = Column(String(64), nullable=True)
    provider_message_id = Column(String(128), nullable=True, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    failure_reason = Column(Text, nullable=True)
    dedup_key = Column(String(191), unique=True, nullable=True)
    delivery_details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """Append-only: application code only ever INSERTs (see services/audit_service.py)."""
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    user_name = Column(String(128), nullable=True)
    role = Column(String(32), nullable=True)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(64), nullable=False)
    resource_id = Column(String(64), nullable=True, index=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    request_id = Column(String(64), nullable=True)
    session_id = Column(String(64), nullable=True)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow, index=True)


# ----------------------------------------------------------------------------------------
# External data & ingestion
# ----------------------------------------------------------------------------------------
class ExternalDataRecord(Base):
    __tablename__ = "external_data_records"

    id = Column(String(64), primary_key=True, index=True)
    provider = Column(String(64), nullable=False, index=True)
    external_id = Column(String(128), nullable=True)
    source = Column(String(128), nullable=False)
    record_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    data_status = Column(String(32), default="LIVE")
    confidence = Column(Float, default=1.0)
    source_timestamp = Column(DateTime, nullable=True)
    request_id = Column(String(64), nullable=True)
    data_version = Column(String(32), nullable=True)
    retrieved_at = Column(DateTime, default=utcnow)


class DataSourceStatus(Base):
    """Health/freshness of every external provider, shown on the admin data-source page."""
    __tablename__ = "data_source_status"

    provider = Column(String(64), primary_key=True)
    category = Column(String(32), nullable=False)
    configured = Column(Boolean, default=False, nullable=False)
    state = Column(String(32), default="CONFIGURATION_REQUIRED")  # LIVE | DEGRADED | UNAVAILABLE | CONFIGURATION_REQUIRED | DEV_ONLY
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    last_latency_ms = Column(Float, nullable=True)
    records_received = Column(Integer, default=0, nullable=False)
    consecutive_failures = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class DataSnapshot(Base):
    __tablename__ = "data_snapshots"

    id = Column(String(64), primary_key=True)
    provider = Column(String(64), nullable=False, index=True)
    dataset = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=False)
    record_count = Column(Integer, default=0)
    quality_report = Column(JSON, default=dict)
    job_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("provider", "dataset", "content_hash", name="uq_snapshot_hash"),)


# ----------------------------------------------------------------------------------------
# Offline sync, idempotency, jobs
# ----------------------------------------------------------------------------------------
class SyncEvent(Base):
    __tablename__ = "sync_events"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    client_sync_id = Column(String(64), nullable=False)
    idempotency_key = Column(String(128), unique=True, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False)
    operation = Column(String(32), nullable=False)
    status = Column(String(32), default="PROCESSED")  # PROCESSED, CONFLICT, FAILED
    result = Column(JSON, default=dict)  # replayed verbatim for duplicate submissions
    device_id = Column(String(128), nullable=True)
    processed_at = Column(DateTime, default=utcnow)


class SyncConflict(Base):
    """Conflicts are persisted, never silently discarded; resolvable via /sync/conflicts."""
    __tablename__ = "sync_conflicts"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=False, index=True)
    base_version = Column(Integer, nullable=True)
    server_version = Column(Integer, nullable=True)
    client_data = Column(JSON, nullable=False)
    server_data = Column(JSON, nullable=False)
    conflicting_fields = Column(JSON, default=list)
    strategy = Column(String(32), nullable=False)
    status = Column(String(32), default="OPEN", index=True)  # OPEN | RESOLVED_CLIENT | RESOLVED_SERVER | RESOLVED_MERGED
    resolved_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("user_scope", "key", name="uq_idem_scope_key"),)

    id = Column(String(64), primary_key=True)
    user_scope = Column(String(64), nullable=False)
    key = Column(String(128), nullable=False)
    method = Column(String(8), nullable=False)
    path = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    status_code = Column(Integer, nullable=True)
    response_body = Column(JSON, nullable=True)
    state = Column(String(16), default="IN_PROGRESS")  # IN_PROGRESS | COMPLETED
    created_at = Column(DateTime, default=utcnow, index=True)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True)
    job_type = Column(String(64), nullable=False, index=True)
    status = Column(String(16), default="QUEUED", nullable=False, index=True)  # QUEUED | RUNNING | COMPLETED | FAILED | RETRYING | DEAD_LETTER
    payload = Column(JSON, default=dict)
    result = Column(JSON, nullable=True)
    attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    error = Column(Text, nullable=True)
    dedup_key = Column(String(191), nullable=True, index=True)
    run_after = Column(DateTime, default=utcnow, index=True)
    created_at = Column(DateTime, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)


class StoredFile(Base):
    __tablename__ = "stored_files"

    id = Column(String(64), primary_key=True)
    owner_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    purpose = Column(String(32), nullable=False)  # VOICE_REPORT | LAB_DOCUMENT | REPORT_PHOTO
    related_entity_type = Column(String(32), nullable=True)
    related_entity_id = Column(String(64), nullable=True, index=True)
    storage_key = Column(String(255), nullable=False, unique=True)  # random name, never the user filename
    content_type = Column(String(64), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    scan_status = Column(String(32), default="PENDING")  # CLEAN | INFECTED | PENDING | NOT_SCANNED
    district = Column(String(128), nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)  # retention (e.g. voice recordings)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
