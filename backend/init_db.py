import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from backend.database import engine, Base, AsyncSessionLocal
from backend.models import (
    User, UserRole, Farm, Herd, Animal, DiseaseReport,
    VeterinaryCase, VeterinaryVisit, Laboratory, LabSample, LabTest,
    VaccinationCampaign, VaccinationRecord, OutbreakEvent, Alert, AuditLog
)
from backend.security import hash_password

async def seed_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if users already seeded
        existing_user = (await db.execute(select(User).limit(1))).scalars().first()
        if existing_user:
            print("Database already seeded.")
            return

        print("Seeding Pashu-Shield database with production reference entities...")

        # 1. Create Users
        users = [
            # Farmer
            User(
                id="FARMER-MH-001",
                email="farmer@pashushield.gov.in",
                phone="9823012345",
                hashed_password=hash_password("Farmer@123"),
                role=UserRole.FARMER.value,
                full_name="Ramesh Tukaram Patil",
                district="Pune",
                taluka="Shirur",
                village="Walwur",
                state="Maharashtra"
            ),
            # Veterinarians
            User(
                id="VET-MH-001",
                email="vet@pashushield.gov.in",
                phone="9823054321",
                hashed_password=hash_password("Vet@123"),
                role=UserRole.VETERINARIAN.value,
                full_name="Dr. Sunita Deshmukh",
                license_number="MSVC-2018-04821",
                qualification="B.V.Sc & A.H., M.V.Sc (Epidemiology)",
                specialization="Large Animal Internal Medicine",
                organization="State Animal Husbandry Department, Shirur Polyclinic",
                service_area="Shirur, Haveli, Khed (Pune)",
                district="Pune",
                taluka="Shirur",
                village="Shirur"
            ),
            User(
                id="VET-MH-002",
                email="vet.satara@pashushield.gov.in",
                phone="9823098765",
                hashed_password=hash_password("Vet@123"),
                role=UserRole.VETERINARIAN.value,
                full_name="Dr. Anil Kulkarni",
                license_number="MSVC-2015-02109",
                qualification="B.V.Sc & A.H.",
                specialization="Ruminant Health & Surgery",
                organization="District Veterinary Polyclinic Satara",
                service_area="Satara, Karad, Koregaon",
                district="Satara",
                taluka="Satara",
                village="Satara"
            ),
            # Lab Technicians
            User(
                id="LAB-MH-001",
                email="lab@pashushield.gov.in",
                phone="9823077777",
                hashed_password=hash_password("Lab@123"),
                role=UserRole.LAB_TECHNICIAN.value,
                full_name="Pooja Shinde (Senior Microbiologist)",
                organization="State Disease Investigation Section (DIS) Pune",
                qualification="M.Sc. Microbiology, NABL Quality Manager",
                district="Pune"
            ),
            # District Officer
            User(
                id="DIST-MH-001",
                email="district@pashushield.gov.in",
                phone="9823088888",
                hashed_password=hash_password("Govt@123"),
                role=UserRole.DISTRICT_OFFICER.value,
                full_name="Dr. Rajesh Joshi (District Animal Husbandry Officer)",
                department="Department of Animal Husbandry, Govt. of Maharashtra",
                designation="DAHO Pune",
                jurisdiction="Pune District",
                district="Pune"
            ),
            # State Surveillance Officer
            User(
                id="STATE-MH-001",
                email="state@pashushield.gov.in",
                phone="9823099999",
                hashed_password=hash_password("Govt@123"),
                role=UserRole.STATE_OFFICER.value,
                full_name="Dr. V. K. Chavan (State Surveillance Coordinator)",
                department="Commissionerate of Animal Husbandry, Maharashtra State",
                designation="Joint Director (Disease Surveillance)",
                jurisdiction="Maharashtra State",
                district="Pune"
            ),
            # System Admin
            User(
                id="ADMIN-MH-001",
                email="admin@pashushield.gov.in",
                phone="9823000000",
                hashed_password=hash_password("Admin@123"),
                role=UserRole.SYSTEM_ADMIN.value,
                full_name="System Administrator (Pashu-Shield Ops)",
                department="IT Directorate, Animal Husbandry",
                designation="Chief System Architect"
            )
        ]
        db.add_all(users)

        # 2. Farms, Herds, Animals
        farm = Farm(
            id="FRM-001",
            owner_id="FARMER-MH-001",
            name="Patil Dairy Farm",
            district="Pune",
            taluka="Shirur",
            village="Walwur",
            lat=18.8288,
            lng=74.3789,
            total_area_acres=4.5
        )
        db.add(farm)

        herd1 = Herd(
            id="HRD-001",
            farm_id="FRM-001",
            owner_id="FARMER-MH-001",
            species="Cattle",
            total_animals=12,
            health_status="Under Observation",
            risk_score=45.0,
            village="Walwur",
            district="Pune",
            lat=18.8288,
            lng=74.3789
        )
        herd2 = Herd(
            id="HRD-002",
            farm_id="FRM-001",
            owner_id="FARMER-MH-001",
            species="Buffalo",
            total_animals=6,
            health_status="Healthy",
            risk_score=10.0,
            village="Walwur",
            district="Pune",
            lat=18.8290,
            lng=74.3792
        )
        db.add_all([herd1, herd2])

        animals = [
            Animal(
                id="ANM-001",
                tag_id="MH-PUN-CAT-001",
                farm_id="FRM-001",
                herd_id="HRD-001",
                owner_id="FARMER-MH-001",
                species="Cattle",
                breed="Gir",
                sex="Female",
                age_years=3.5,
                health_status="Under Observation",
                risk_score=65.0,
                village="Walwur",
                district="Pune",
                lat=18.8288,
                lng=74.3789
            ),
            Animal(
                id="ANM-002",
                tag_id="MH-PUN-CAT-002",
                farm_id="FRM-001",
                herd_id="HRD-001",
                owner_id="FARMER-MH-001",
                species="Cattle",
                breed="Khillari",
                sex="Male",
                age_years=4.0,
                health_status="Healthy",
                risk_score=15.0,
                village="Walwur",
                district="Pune",
                lat=18.8288,
                lng=74.3789
            ),
            Animal(
                id="ANM-003",
                tag_id="MH-PUN-BUF-001",
                farm_id="FRM-001",
                herd_id="HRD-002",
                owner_id="FARMER-MH-001",
                species="Buffalo",
                breed="Murrah",
                sex="Female",
                age_years=5.0,
                health_status="Healthy",
                risk_score=12.0,
                village="Walwur",
                district="Pune",
                lat=18.8290,
                lng=74.3792
            )
        ]
        db.add_all(animals)

        # 3. Disease Reports & Cases
        report1 = DiseaseReport(
            id="REP-001",
            report_number="MH-PUN-260901-A101",
            user_id="FARMER-MH-001",
            reporter_name="Ramesh Tukaram Patil",
            reporter_role="FARMER",
            species="Cattle",
            number_affected=3,
            number_dead=0,
            symptoms=["Fever", "Blisters on gums", "Excessive salivation", "Lameness"],
            temperature=104.5,
            district="Pune",
            taluka="Shirur",
            village="Walwur",
            lat=18.8288,
            lng=74.3789,
            suspected_disease="Foot-and-Mouth Disease (FMD)",
            status="Under Review",
            triage_urgency="URGENT",
            triage_risk_level="HIGH",
            triage_recommendations=[
                "Immediately quarantine in separate shed.",
                "Wash mouth/feet with mild antiseptic solution.",
                "Restrict movement of farm personnel and vehicles."
            ],
            notes="Observed high salivation and reluctance to stand since yesterday morning.",
            source="LIVE"
        )
        db.add(report1)

        case1 = VeterinaryCase(
            id="VET-2026-004821",
            case_number="CAS-PUN-260901-0048",
            report_id="REP-001",
            animal_id="ANM-001",
            herd_id="HRD-001",
            farmer_id="FARMER-MH-001",
            assigned_vet_id="VET-MH-001",
            status="Under Examination",
            priority="HIGH",
            species="Cattle",
            district="Pune",
            village="Shirur, Walwur",
            lat=18.8288,
            lng=74.3789,
            reported_problem="Severe oral blisters, pyrexia 104.5 F, reduced lactation",
            diagnosis="Suspected FMD Serotype O. Awaiting confirmatory RT-PCR.",
            treatment_prescribed="Boroglycerine oral rinse, Meloxicam analgesia, protective soft diet",
            risk_score=78.0,
            assigned_at=datetime.utcnow() - timedelta(hours=5),
            accepted_at=datetime.utcnow() - timedelta(hours=4),
            en_route_at=datetime.utcnow() - timedelta(hours=3),
            on_site_at=datetime.utcnow() - timedelta(hours=2)
        )
        case2 = VeterinaryCase(
            id="VET-2026-004822",
            case_number="CAS-SAT-260902-0049",
            species="Goat",
            district="Satara",
            village="Mhaswad",
            lat=17.6805,
            lng=74.0183,
            reported_problem="Nodular skin lesions, high fever, nasal discharge",
            diagnosis="Suspected Goat Pox",
            priority="CRITICAL",
            status="En Route",
            risk_score=88.0,
            assigned_vet_id="VET-MH-002",
            assigned_at=datetime.utcnow() - timedelta(hours=1),
            accepted_at=datetime.utcnow() - timedelta(minutes=45),
            en_route_at=datetime.utcnow() - timedelta(minutes=20)
        )
        db.add_all([case1, case2])

        # 4. Laboratories, Samples, Tests
        lab = Laboratory(
            id="LAB-FAC-001",
            name="State Disease Investigation Section (DIS) Pune",
            code="DIS-PUN-01",
            district="Pune",
            state="Maharashtra",
            address="Aundh Road, Ganeshkhind, Pune 411007",
            lat=18.5420,
            lng=73.8180,
            contact_phone="020-25651234",
            contact_email="dispune@mahavet.gov.in",
            accreditation="NABL ISO/IEC 17025:2017 Accredited",
            services=["RT-PCR", "ELISA Serology", "Histopathology", "Culture & Antibiotic Sensitivity"]
        )
        db.add(lab)

        sample1 = LabSample(
            id="SMP-10231",
            sample_code="SMP-PUN-2609-10231",
            case_id="VET-2026-004821",
            animal_id="ANM-001",
            farmer_id="FARMER-MH-001",
            lab_id="LAB-FAC-001",
            collected_by_id="VET-MH-001",
            species="Cattle",
            disease_suspected="Foot-and-Mouth Disease (FMD)",
            sample_type="Vesicular Epithelium & Serum",
            priority="Critical",
            status="Testing",
            collection_date=datetime.utcnow() - timedelta(hours=3),
            received_at=datetime.utcnow() - timedelta(hours=1),
            tested_at=datetime.utcnow() - timedelta(minutes=30),
            district="Pune",
            location="Shirur, Pune",
            qr_code="PASHU:SAMPLE:SMP-PUN-2609-10231"
        )
        db.add(sample1)

        test1 = LabTest(
            id="TST-001",
            sample_id="SMP-10231",
            test_name="RT-PCR for FMD Viral RNA",
            status="In Progress",
            remarks="Amplification cycle in progress"
        )
        test2 = LabTest(
            id="TST-002",
            sample_id="SMP-10231",
            test_name="LPBE ELISA (Serotype Identification)",
            status="Pending"
        )
        db.add_all([test1, test2])

        # 5. Vaccination Campaigns and Records
        campaign1 = VaccinationCampaign(
            id="CMP-001",
            campaign_code="NADCP-FMD-R5-2026",
            name="NADCP FMD National Vaccination Round 5",
            disease="Foot-and-Mouth Disease (FMD)",
            vaccine="Raksha-Ovac Trivalent (O, A, Asia-1)",
            species=["Cattle", "Buffalo"],
            target_districts=["Pune", "Satara", "Kolhapur", "Solapur", "Ahmednagar", "Nashik"],
            start_date=datetime.utcnow() - timedelta(days=20),
            end_date=datetime.utcnow() + timedelta(days=40),
            status="Active",
            target_population=1800000,
            coverage_target_percent=85.0,
            current_vaccinated=1412000
        )
        campaign2 = VaccinationCampaign(
            id="CMP-002",
            campaign_code="LSD-IMMUN-2026",
            name="State-wide Lumpy Skin Disease Immunization Drive",
            disease="Lumpy Skin Disease (LSD)",
            vaccine="Lumpi-ProVacInd (Attenuated)",
            species=["Cattle"],
            target_districts=["All 36 Maharashtra Districts"],
            start_date=datetime.utcnow() - timedelta(days=60),
            end_date=datetime.utcnow() - timedelta(days=5),
            status="Completed",
            target_population=2400000,
            coverage_target_percent=90.0,
            current_vaccinated=2280000
        )
        db.add_all([campaign1, campaign2])

        v_rec = VaccinationRecord(
            id="VAC-001",
            animal_id="ANM-001",
            herd_id="HRD-001",
            species="Cattle",
            disease="Foot-and-Mouth Disease (FMD)",
            vaccine="Raksha-Ovac Trivalent",
            batch_number="RO-2026-B81",
            vaccination_date=datetime.utcnow() - timedelta(days=45),
            next_due_date=datetime.utcnow() + timedelta(days=135),
            campaign_id="CMP-001",
            provider_id="VET-MH-001",
            provider_name="Dr. Sunita Deshmukh",
            location="Walwur, Shirur",
            district="Pune"
        )
        db.add(v_rec)

        # 6. Outbreak events
        outbreak1 = OutbreakEvent(
            id="OB-001",
            outbreak_code="OUT-2609-PUN-01",
            disease="Foot-and-Mouth Disease (FMD)",
            district="Pune",
            taluka="Shirur",
            village="Walwur",
            center_lat=18.8288,
            center_lng=74.3789,
            radius_km=7.5,
            affected_count=34,
            death_count=1,
            status="Active",
            severity="High",
            date_detected=datetime.utcnow() - timedelta(days=5)
        )
        db.add(outbreak1)

        # 7. Alerts
        alerts = [
            Alert(
                id="ALT-001",
                alert_code="ALR-2609-001",
                type="high",
                severity="CRITICAL",
                title="Critical Outbreak Cluster - Shirur, Pune (FMD)",
                message="Confirmed cluster of vesicular lesions. Mobile Veterinary Unit dispatched; containment ring active.",
                district="Pune",
                disease="FMD",
                is_broadcast=True
            ),
            Alert(
                id="ALT-002",
                alert_code="ALR-2609-002",
                type="warning",
                severity="HIGH",
                title="FMD Suspected Case Reported - Satara",
                message="Syndromic reporting surge in Karad block. Active surveillance notified.",
                district="Satara",
                disease="FMD",
                is_broadcast=True
            )
        ]
        db.add_all(alerts)

        # 8. Audit Logs
        audit = AuditLog(
            id="AUD-001",
            user_id="SYSTEM",
            user_name="System Initialization",
            role="SYSTEM_ADMIN",
            action="SYSTEM_INIT",
            resource="DATABASE",
            resource_id="INITIAL_SEED",
            old_value=None,
            new_value={"version": "2.0.0", "status": "READY"},
            ip_address="127.0.0.1",
            success=True,
            created_at=datetime.utcnow()
        )
        db.add(audit)

        await db.commit()
        print("Database seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_database())
