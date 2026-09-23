"""Unit tests for pure service logic."""
import os
from datetime import datetime

import pytest
from fastapi import HTTPException

import tests.conftest  # noqa: F401  (sets env before backend import)
from backend.config import ConfigurationError, Settings, validate_for_environment
from backend.services import file_service, workflow
from backend.services.ml_service import ml_service
from backend.services.outbreak_service import cluster_points
from backend.services.spatial import haversine_distance, valid_coordinates
from backend.services.triage_service import TemperatureError, TriageEngine, normalize_temperature


# --- triage -------------------------------------------------------------------------------
def test_temperature_units():
    assert normalize_temperature(104, "F")[0] == pytest.approx(40.0)
    assert normalize_temperature(40, "C")[0] == 40
    c, unit, inferred = normalize_temperature(104, None)
    assert unit == "F" and inferred
    with pytest.raises(TemperatureError):
        normalize_temperature(120, "C")
    with pytest.raises(TemperatureError):
        normalize_temperature(float("nan"), "C")


def test_same_fever_in_c_and_f_gives_same_risk():
    a = TriageEngine.evaluate("Cattle", ["Fever"], 1, 0, 41.0, None, "C")
    b = TriageEngine.evaluate("Cattle", ["Fever"], 1, 0, 105.8, None, "F")
    assert a["risk_level"] == b["risk_level"]


def test_triage_explanations_and_disclaimer():
    r = TriageEngine.evaluate("Cattle", ["Sudden death"], 5, 2)
    assert r["risk_level"] == "CRITICAL" and r["is_diagnosis"] is False
    assert r["explanation"] and r["rule_version"]


# --- workflow ----------------------------------------------------------------------------
def test_workflow_transitions():
    assert workflow.can_transition("CASE", "REPORTED", "ASSIGNED")
    assert not workflow.can_transition("CASE", "REPORTED", "RESOLVED")
    assert not workflow.can_transition("CASE", "CLOSED", "ASSIGNED")
    assert workflow.normalize_status("En Route") == "EN_ROUTE"
    with pytest.raises(HTTPException) as e:
        workflow.assert_transition("SAMPLE", "COLLECTED", "VERIFIED")
    assert e.value.status_code == 409


# --- spatial / clustering -------------------------------------------------------------------
def test_haversine_and_coords():
    assert haversine_distance(18.52, 73.85, 18.52, 73.85) == 0
    assert 110 < haversine_distance(0, 0, 1, 0) < 112
    assert not valid_coordinates(0, 0) and not valid_coordinates(None, 73) and valid_coordinates(18.5, 73.8)


def test_clusters_from_real_points_only():
    now = datetime.utcnow()
    pts = [{"id": str(i), "disease": "LSD", "district": "Pune", "lat": 18.5 + i * 0.01, "lng": 73.8, "cases": 2, "deaths": 0, "at": now,
            "evidence": "REPORTED", "source_type": "FARMER_REPORT", "is_demo": False} for i in range(3)]
    pts.append({**pts[0], "id": "far", "lat": 20.0})
    clusters = cluster_points(pts, eps_km=5, min_reports=2)
    assert len(clusters) == 1 and clusters[0]["record_count"] == 3 and clusters[0]["evidence_level"] == "REPORTED"
    assert cluster_points([], 5, 2) == []


# --- ML -----------------------------------------------------------------------------------
def test_forecast_insufficient_and_ok():
    assert ml_service.forecast([1, 2, 3], 7)["status"] == "INSUFFICIENT_DATA"
    fc = ml_service.forecast([float(x) for x in range(1, 21)], 7)
    assert fc["status"] == "OK" and len(fc["forecast"]) == 7
    assert all(p["lower"] <= p["upper"] for p in fc["forecast"])


def test_predict_missing_features():
    r = ml_service.predict_risk({"disease": "LSD"})
    assert r["status"] == "INSUFFICIENT_DATA" and r["missing_features"]


# --- uploads ------------------------------------------------------------------------------
def test_upload_validation():
    assert file_service.validate_upload("a.wav", "audio/wav", b"RIFF\x00\x00\x00\x00WAVEfmt ", "VOICE_REPORT") == "audio/wav"
    with pytest.raises(HTTPException):
        file_service.validate_upload("a.wav", "audio/wav", b"MZ\x90\x00", "VOICE_REPORT")
    with pytest.raises(HTTPException):
        file_service.validate_upload("a.exe", "audio/wav", b"RIFF\x00\x00\x00\x00WAVE", "VOICE_REPORT")
    with pytest.raises(HTTPException):
        file_service.resolve_path("../../etc/passwd")


# --- config -------------------------------------------------------------------------------
def test_production_config_rejects_insecure_defaults(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATA_MODE", "demo")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ConfigurationError) as e:
        validate_for_environment(Settings())
    msg = str(e.value)
    assert "JWT_SECRET" in msg and "DATA_MODE=live" in msg and "CORS" in msg
    os.environ["ENVIRONMENT"] = "test"
