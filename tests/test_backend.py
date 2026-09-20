import pytest
import pytest_asyncio
import httpx
from backend.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Pashu-Shield API"

@pytest.mark.asyncio
async def test_demo_login_and_auth():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Test Farmer Login
        res_farmer = await client.post("/api/v1/auth/demo-login/farmer")
        assert res_farmer.status_code == 200
        f_data = res_farmer.json()
        assert "access_token" in f_data
        assert f_data["user"]["role"] == "FARMER"

        # Test Vet Login
        res_vet = await client.post("/api/v1/auth/demo-login/veterinarian")
        assert res_vet.status_code == 200
        v_data = res_vet.json()
        assert v_data["user"]["role"] == "VETERINARIAN"

        # Test Lab Login
        res_lab = await client.post("/api/v1/auth/demo-login/lab")
        assert res_lab.status_code == 200
        l_data = res_lab.json()
        assert l_data["user"]["role"] == "LAB_TECHNICIAN"

        # Test District Officer Login
        res_govt = await client.post("/api/v1/auth/demo-login/district")
        assert res_govt.status_code == 200
        assert res_govt.json()["user"]["role"] == "DISTRICT_OFFICER"

@pytest.mark.asyncio
async def test_disease_reporting_and_triage():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Submit a critical disease report
        report_payload = {
            "species": "Cattle",
            "number_affected": 3,
            "number_dead": 1,
            "symptoms": ["High Fever", "Blisters on gums", "Severe lameness"],
            "temperature": 105.0,
            "district": "Pune",
            "village": "Shirur",
            "suspected_disease": "Foot-and-Mouth Disease (FMD)",
            "notes": "Critical symptoms observed in milk cattle"
        }
        res = await client.post("/api/v1/reports", json=report_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["triage"]["risk_level"] == "CRITICAL"
        assert data["triage"]["urgency"] == "EMERGENCY"
        assert data["assignedCase"] is not None
        assert "caseNumber" in data["assignedCase"]

@pytest.mark.asyncio
async def test_case_lifecycle():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Get vet login
        login_res = await client.post("/api/v1/auth/demo-login/veterinarian")
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List cases
        cases_res = await client.get("/api/v1/cases", headers=headers)
        assert cases_res.status_code == 200
        cases = cases_res.json()
        assert len(cases) > 0
        case_id = cases[0]["id"]

        # Update case status to ACCEPTED then EN_ROUTE
        up_res1 = await client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "ACCEPTED", "diagnosis": "Clinical exam scheduled"},
            headers=headers
        )
        assert up_res1.status_code == 200

        up_res2 = await client.patch(
            f"/api/v1/cases/{case_id}/status",
            json={"status": "EN_ROUTE"},
            headers=headers
        )
        assert up_res2.status_code == 200
        assert up_res2.json()["case"]["status"] == "EN_ROUTE"

@pytest.mark.asyncio
async def test_lab_lifecycle_and_verification():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login as Lab Technician
        login_res = await client.post("/api/v1/auth/demo-login/lab")
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Register sample
        sample_payload = {
            "species": "Cattle",
            "disease_suspected": "Foot-and-Mouth Disease (FMD)",
            "sample_type": "Serum",
            "priority": "Urgent",
            "district": "Pune",
            "location": "Shirur",
            "tests": ["RT-PCR"]
        }
        create_res = await client.post("/api/v1/labs/samples", json=sample_payload, headers=headers)
        assert create_res.status_code == 200
        sample_id = create_res.json()["sample_id"]

        # Advance sample status
        status_res = await client.patch(
            f"/api/v1/labs/samples/{sample_id}/status",
            json={"status": "TESTING"},
            headers=headers
        )
        assert status_res.status_code == 200

        # Verify sample result
        verify_res = await client.post(
            f"/api/v1/labs/samples/{sample_id}/verify",
            json={"remarks": "RT-PCR positive for FMD Serotype O. Confirmatory sequence aligned."},
            headers=headers
        )
        assert verify_res.status_code == 200

@pytest.mark.asyncio
async def test_offline_sync_push_idempotency():
    import uuid
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        key = f"test-idempotency-key-{uuid.uuid4().hex}"
        sync_payload = {
            "items": [
                {
                    "idempotency_key": key,
                    "store": "animals",
                    "id": "LOCAL-ANM-101",
                    "operation": "CREATE",
                    "data": {
                        "tagId": "MH-PUN-TEST-101",
                        "species": "Cattle",
                        "breed": "Gir",
                        "district": "Pune",
                        "village": "Shirur"
                    }
                }
            ]
        }
        # First push
        res1 = await client.post("/api/v1/sync/push", json=sync_payload)
        assert res1.status_code == 200
        assert res1.json()["processed"][0]["status"] == "SYNCED"

        # Duplicate push with same idempotency key
        res2 = await client.post("/api/v1/sync/push", json=sync_payload)
        assert res2.status_code == 200
        assert res2.json()["processed"][0]["status"] == "ALREADY_SYNCED"

@pytest.mark.asyncio
async def test_voice_intent_extractor():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Farmer voice: "I have 2 sick cows with fever and blisters"
        res = await client.post(
            "/api/v1/voice/intent",
            json={"transcript": "I have 2 sick cows with fever and blisters", "language": "en"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "REPORT_DISEASE"
        assert data["entities"]["species"] == "Cattle"
        assert data["entities"]["number_affected"] == 2
        assert "Fever" in data["entities"]["symptoms"]
        assert data["requires_confirmation"] is True

@pytest.mark.asyncio
async def test_ml_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Prediction
        pred_res = await client.post(
            "/api/predict",
            json={
                "disease": "LSD",
                "district": "Pune",
                "time_range": "14",
                "animal_population": 15000,
                "affected_animals": 120,
                "new_cases": 45,
                "deaths": 5,
                "vaccination_coverage": 0.45,
                "temperature": 32.5,
                "rainfall": 12.0,
                "humidity": 65.0,
                "animal_density": 120.5,
                "previous_cases": 300,
                "cases_growth_rate": 0.15
            }
        )
        assert pred_res.status_code == 200
        pred = pred_res.json()
        assert "risk_score" in pred
        assert "risk_level" in pred
        assert "top_risk_factors" in pred

        # Outbreak detection
        ob_res = await client.post(
            "/api/outbreak-detection",
            json={"new_cases": 80, "cases_growth_rate": 0.6, "deaths": 8, "district": "Pune"}
        )
        assert ob_res.status_code == 200
        assert "outbreak_detected" in ob_res.json()

@pytest.mark.asyncio
async def test_role_specific_logins_and_signups():
    import uuid
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test Seeded Logins
        credentials = [
            ("farmer@pashushield.gov.in", "Farmer@123", "FARMER"),
            ("vet@pashushield.gov.in", "Vet@123", "VETERINARIAN"),
            ("lab@pashushield.gov.in", "Lab@123", "LAB_TECHNICIAN"),
            ("state@pashushield.gov.in", "Govt@123", "STATE_OFFICER"),
            ("admin@pashushield.gov.in", "Govt@123", "SYSTEM_ADMIN"),
        ]
        for email, pwd, expected_role in credentials:
            res = await client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
            assert res.status_code == 200, f"Login failed for {email}"
            data = res.json()
            assert "access_token" in data
            assert data["user"]["role"] == expected_role

        # 2. Test Sign Up for Farmer
        uid = uuid.uuid4().hex[:6]
        f_res = await client.post("/api/v1/auth/signup/farmer", json={
            "full_name": f"Farmer Test {uid}",
            "phone": f"99{uid[:8]}",
            "email": f"farmer_{uid}@example.com",
            "password": "Password@123",
            "district": "Satara",
            "village": "Karad"
        })
        assert f_res.status_code == 200
        assert f_res.json()["user"]["role"] == "FARMER"

        # 3. Test Sign Up for Vet
        v_res = await client.post("/api/v1/auth/signup/vet", json={
            "full_name": f"Dr. Vet Test {uid}",
            "phone": f"98{uid[:8]}",
            "email": f"vet_{uid}@example.com",
            "password": "Password@123",
            "license_number": f"MSVC-{uid}",
            "qualification": "B.V.Sc & A.H.",
            "district": "Pune"
        })
        assert v_res.status_code == 200
        assert v_res.json()["user"]["role"] == "VETERINARIAN"

        # 4. Test Sign Up for Lab
        l_res = await client.post("/api/v1/auth/signup/lab", json={
            "lab_name": f"Test Diagnostic Lab {uid}",
            "email": f"lab_{uid}@example.com",
            "phone": f"97{uid[:8]}",
            "password": "Password@123",
            "district": "Pune"
        })
        assert l_res.status_code == 200
        assert l_res.json()["user"]["role"] == "LAB_TECHNICIAN"

        # 5. Test Sign Up for Government Official / Admin
        g_res = await client.post("/api/v1/auth/signup/government", json={
            "full_name": f"Dr. Officer Test {uid}",
            "email": f"govt_{uid}@example.com",
            "phone": f"96{uid[:8]}",
            "password": "Password@123",
            "district": "Pune",
            "role": "STATE_OFFICER"
        })
        assert g_res.status_code == 200
        assert g_res.json()["user"]["role"] == "STATE_OFFICER"
