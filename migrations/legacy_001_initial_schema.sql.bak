-- Pashu-Shield Production Database Schema
-- Target: PostgreSQL 14+ with PostGIS Extension

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- 1. Users & Authentication
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(32),
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'FARMER',
    full_name VARCHAR(255) NOT NULL,
    state VARCHAR(128) DEFAULT 'Maharashtra',
    division VARCHAR(128),
    district VARCHAR(128),
    taluka VARCHAR(128),
    village VARCHAR(128),
    license_number VARCHAR(128),
    qualification VARCHAR(255),
    specialization VARCHAR(255),
    organization VARCHAR(255),
    service_area VARCHAR(255),
    designation VARCHAR(128),
    department VARCHAR(128),
    jurisdiction VARCHAR(128),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT TRUE,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_district ON users(district);

-- 2. Farms, Herds, Animals
CREATE TABLE IF NOT EXISTS farms (
    id VARCHAR(64) PRIMARY KEY,
    owner_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    district VARCHAR(128) NOT NULL,
    taluka VARCHAR(128),
    village VARCHAR(128) NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    total_area_acres DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS herds (
    id VARCHAR(64) PRIMARY KEY,
    farm_id VARCHAR(64) REFERENCES farms(id) ON DELETE SET NULL,
    owner_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    species VARCHAR(64) NOT NULL,
    total_animals INT DEFAULT 1,
    health_status VARCHAR(64) DEFAULT 'Healthy',
    risk_score DOUBLE PRECISION DEFAULT 0.0,
    village VARCHAR(128) NOT NULL,
    district VARCHAR(128) NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS animals (
    id VARCHAR(64) PRIMARY KEY,
    tag_id VARCHAR(64) NOT NULL,
    farm_id VARCHAR(64) REFERENCES farms(id) ON DELETE SET NULL,
    herd_id VARCHAR(64) REFERENCES herds(id) ON DELETE SET NULL,
    owner_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
    species VARCHAR(64) NOT NULL,
    breed VARCHAR(128),
    sex VARCHAR(16) DEFAULT 'Female',
    age_years DOUBLE PRECISION DEFAULT 2.0,
    health_status VARCHAR(64) DEFAULT 'Healthy',
    risk_score DOUBLE PRECISION DEFAULT 0.0,
    village VARCHAR(128) NOT NULL,
    district VARCHAR(128) NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_animals_tag ON animals(tag_id);
CREATE INDEX IF NOT EXISTS idx_animals_owner ON animals(owner_id);

-- 3. Disease Reports & Case Dispatch
CREATE TABLE IF NOT EXISTS disease_reports (
    id VARCHAR(64) PRIMARY KEY,
    report_number VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    reporter_name VARCHAR(255),
    reporter_role VARCHAR(32) DEFAULT 'FARMER',
    species VARCHAR(64) NOT NULL,
    number_affected INT DEFAULT 1,
    number_dead INT DEFAULT 0,
    symptoms JSONB DEFAULT '[]'::jsonb,
    temperature DOUBLE PRECISION,
    district VARCHAR(128) NOT NULL,
    taluka VARCHAR(128),
    village VARCHAR(128) NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    suspected_disease VARCHAR(128) DEFAULT 'Unknown',
    status VARCHAR(32) DEFAULT 'Suspected',
    triage_urgency VARCHAR(32) DEFAULT 'NORMAL',
    triage_risk_level VARCHAR(32) DEFAULT 'MODERATE',
    triage_recommendations JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    is_demo BOOLEAN DEFAULT FALSE,
    source VARCHAR(32) DEFAULT 'LIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_district ON disease_reports(district);
CREATE INDEX IF NOT EXISTS idx_reports_status ON disease_reports(status);

CREATE TABLE IF NOT EXISTS veterinary_cases (
    id VARCHAR(64) PRIMARY KEY,
    case_number VARCHAR(64) UNIQUE NOT NULL,
    report_id VARCHAR(64) REFERENCES disease_reports(id) ON DELETE SET NULL,
    animal_id VARCHAR(64) REFERENCES animals(id) ON DELETE SET NULL,
    herd_id VARCHAR(64) REFERENCES herds(id) ON DELETE SET NULL,
    farmer_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    assigned_vet_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(64) DEFAULT 'REPORTED',
    priority VARCHAR(32) DEFAULT 'HIGH',
    species VARCHAR(64) NOT NULL,
    district VARCHAR(128) NOT NULL,
    village VARCHAR(128) NOT NULL,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    reported_problem TEXT,
    diagnosis TEXT,
    treatment_prescribed TEXT,
    risk_score DOUBLE PRECISION DEFAULT 50.0,
    assigned_at TIMESTAMP WITH TIME ZONE,
    accepted_at TIMESTAMP WITH TIME ZONE,
    en_route_at TIMESTAMP WITH TIME ZONE,
    on_site_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Laboratories, Samples, Tests
CREATE TABLE IF NOT EXISTS laboratories (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    district VARCHAR(128) NOT NULL,
    state VARCHAR(128) DEFAULT 'Maharashtra',
    address VARCHAR(255),
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    contact_phone VARCHAR(32),
    contact_email VARCHAR(255),
    accreditation VARCHAR(128) DEFAULT 'NABL Accredited',
    services JSONB DEFAULT '[]'::jsonb,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS lab_samples (
    id VARCHAR(64) PRIMARY KEY,
    sample_code VARCHAR(64) UNIQUE NOT NULL,
    case_id VARCHAR(64) REFERENCES veterinary_cases(id) ON DELETE SET NULL,
    animal_id VARCHAR(64),
    farmer_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    lab_id VARCHAR(64) REFERENCES laboratories(id) ON DELETE SET NULL,
    collected_by_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    species VARCHAR(64) NOT NULL,
    disease_suspected VARCHAR(128) NOT NULL,
    sample_type VARCHAR(64) NOT NULL,
    priority VARCHAR(32) DEFAULT 'Routine',
    status VARCHAR(64) DEFAULT 'COLLECTED',
    collection_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    received_at TIMESTAMP WITH TIME ZONE,
    tested_at TIMESTAMP WITH TIME ZONE,
    verified_at TIMESTAMP WITH TIME ZONE,
    location VARCHAR(128),
    district VARCHAR(128) NOT NULL,
    qr_code VARCHAR(128),
    notes TEXT,
    verified_by_id VARCHAR(64),
    verified_by_name VARCHAR(128),
    verification_remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lab_tests (
    id VARCHAR(64) PRIMARY KEY,
    sample_id VARCHAR(64) REFERENCES lab_samples(id) ON DELETE CASCADE,
    test_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) DEFAULT 'Pending',
    result VARCHAR(32),
    value VARCHAR(128),
    remarks TEXT,
    tested_by_id VARCHAR(64),
    tested_at TIMESTAMP WITH TIME ZONE
);

-- 5. Vaccination Campaigns and Records
CREATE TABLE IF NOT EXISTS vaccination_campaigns (
    id VARCHAR(64) PRIMARY KEY,
    campaign_code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    disease VARCHAR(128) NOT NULL,
    vaccine VARCHAR(128) NOT NULL,
    species JSONB DEFAULT '[]'::jsonb,
    target_districts JSONB DEFAULT '[]'::jsonb,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) DEFAULT 'Active',
    target_population INT DEFAULT 100000,
    coverage_target_percent DOUBLE PRECISION DEFAULT 85.0,
    current_vaccinated INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vaccination_records (
    id VARCHAR(64) PRIMARY KEY,
    animal_id VARCHAR(64) NOT NULL,
    herd_id VARCHAR(64),
    species VARCHAR(64) NOT NULL,
    disease VARCHAR(128) NOT NULL,
    vaccine VARCHAR(128) NOT NULL,
    batch_number VARCHAR(64) NOT NULL,
    vaccination_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    next_due_date TIMESTAMP WITH TIME ZONE,
    campaign_id VARCHAR(64) REFERENCES vaccination_campaigns(id) ON DELETE SET NULL,
    provider_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    provider_name VARCHAR(128),
    location VARCHAR(128),
    district VARCHAR(128) NOT NULL,
    status VARCHAR(32) DEFAULT 'Administered'
);

-- 6. Alerts, Audit Logs, Sync Events
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(64) PRIMARY KEY,
    alert_code VARCHAR(64) UNIQUE NOT NULL,
    type VARCHAR(32) DEFAULT 'warning',
    severity VARCHAR(32) DEFAULT 'HIGH',
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    district VARCHAR(128),
    taluka VARCHAR(128),
    disease VARCHAR(128),
    is_broadcast BOOLEAN DEFAULT FALSE,
    target_roles JSONB DEFAULT '[]'::jsonb,
    read_by JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64),
    user_name VARCHAR(128),
    role VARCHAR(32),
    action VARCHAR(64) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    resource_id VARCHAR(64),
    old_value JSONB,
    new_value JSONB,
    ip_address VARCHAR(64),
    success BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS external_data_records (
    id VARCHAR(64) PRIMARY KEY,
    provider VARCHAR(64) NOT NULL,
    external_id VARCHAR(128),
    source VARCHAR(128) NOT NULL,
    record_type VARCHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    data_status VARCHAR(32) DEFAULT 'LIVE',
    confidence DOUBLE PRECISION DEFAULT 1.0,
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sync_events (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    client_sync_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    operation VARCHAR(32) NOT NULL,
    status VARCHAR(32) DEFAULT 'PROCESSED',
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
