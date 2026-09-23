"""
Canonical ML service (the single risk engine for the platform; ml-backend/main.py now only
re-exports this module so there are no competing implementations).

Honesty rules:
  * The bundled Random Forest was trained on SYNTHETIC data. Every output says so via
    `model.validation_status = "NOT_VALIDATED_SYNTHETIC"`, and metrics are reported as
    synthetic-holdout metrics, never as clinical/epidemiological accuracy.
  * Predictions are "PREDICTED RISK — NOT A CONFIRMED DIAGNOSIS". Veterinary / laboratory
    confirmation remains authoritative.
  * Model artefacts are only unpickled if their SHA-256 matches models/model_card.json
    (prevents loading a tampered pickle = arbitrary code execution).
  * Forecasting returns INSUFFICIENT_DATA instead of extrapolating short series.
  * Outbreak clusters are computed from persisted reports/observations (outbreak_service.py);
    the previous hardcoded/random cluster generator was removed.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pashu_shield.ml")

FEATURE_COLS = [
    "animal_population", "affected_animals", "new_cases", "deaths",
    "vaccination_coverage", "temperature", "rainfall", "humidity",
    "animal_density", "previous_cases", "cases_growth_rate",
]
PREDICTION_LABEL = "PREDICTED RISK — NOT A CONFIRMED DIAGNOSIS"
MIN_FORECAST_POINTS = 8


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class MLService:
    def __init__(self, models_dir: Optional[Path] = None) -> None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.models_dir = models_dir or base_dir / "ml-backend" / "models"
        self.rf_model = None
        self.scaler = None
        self.iso_model = None
        self.card: Dict[str, Any] = {}
        self.load_error: Optional[str] = None
        self._load_models()

    # ------------------------------------------------------------------------------------
    def _load_models(self) -> None:
        card_path = self.models_dir / "model_card.json"
        if not card_path.exists():
            self.load_error = "model_card.json missing; refusing to unpickle unverified artefacts"
            return
        try:
            self.card = json.loads(card_path.read_text())
            import joblib  # local import: heavy dependency
            for attr, fname in (("rf_model", "rf_model.pkl"), ("scaler", "scaler.pkl"), ("iso_model", "iso_model.pkl")):
                path = self.models_dir / fname
                expected = (self.card.get("artifacts") or {}).get(fname)
                if not path.exists() or not expected:
                    continue
                if _sha256(path) != expected:
                    self.load_error = f"checksum mismatch for {fname}; artefact not loaded"
                    logger.error(self.load_error)
                    continue
                setattr(self, attr, joblib.load(path))
        except Exception as e:  # pragma: no cover - depends on environment
            self.load_error = f"model load failed: {type(e).__name__}"
            logger.warning(self.load_error)

    @property
    def model_loaded(self) -> bool:
        return self.rf_model is not None and self.scaler is not None

    def model_info(self) -> Dict[str, Any]:
        return {
            "model_version": self.card.get("model_version", "unversioned"),
            "algorithm": self.card.get("algorithm", "RandomForestClassifier"),
            "training_dataset": self.card.get("training_dataset", "unknown"),
            "training_data_type": self.card.get("training_data_type", "SYNTHETIC"),
            "training_date": self.card.get("training_date"),
            "features": self.card.get("features", FEATURE_COLS),
            "thresholds": self.card.get("thresholds", {"high": 0.6, "moderate": 0.3}),
            "validation_status": self.card.get("validation_status", "NOT_VALIDATED_SYNTHETIC"),
            "engine": "random_forest" if self.model_loaded else "deterministic_fallback",
            "load_error": self.load_error,
        }

    @property
    def metrics(self) -> Dict[str, Any]:
        """Kept for the existing /model-performance consumers; adds explicit provenance."""
        m = dict(self.card.get("metrics", {}))
        return {
            "model": self.card.get("algorithm", "Random Forest"),
            "accuracy": m.get("accuracy"),
            "precision": m.get("precision"),
            "recall": m.get("recall"),
            "f1_score": m.get("f1_score"),
            "roc_auc": m.get("roc_auc"),
            "pr_auc": m.get("pr_auc"),
            "sensitivity": m.get("recall"),
            "specificity": m.get("specificity"),
            "brier_score": m.get("brier_score"),
            "confusion_matrix": m.get("confusion_matrix"),
            "training_samples": self.card.get("training_samples"),
            "last_trained": self.card.get("training_date"),
            "evaluation_split": self.card.get("evaluation_split"),
            "training_data_type": self.card.get("training_data_type", "SYNTHETIC"),
            "data_provenance": "SYNTHETIC HOLD-OUT METRICS — not evidence of real-world accuracy",
            "validation_status": self.card.get("validation_status", "NOT_VALIDATED_SYNTHETIC"),
            "model_version": self.card.get("model_version", "unversioned"),
        }

    # ------------------------------------------------------------------------------------
    def predict_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        row = {c: float(data[c]) for c in FEATURE_COLS if data.get(c) is not None}
        missing = [c for c in FEATURE_COLS if c not in row]
        if missing:
            return {"status": "INSUFFICIENT_DATA", "missing_features": missing, "label": PREDICTION_LABEL, "model": self.model_info()}
        thresholds = self.model_info()["thresholds"]
        if self.model_loaded:
            import pandas as pd
            df = pd.DataFrame([row])[FEATURE_COLS]
            prob = float(self.rf_model.predict_proba(self.scaler.transform(df))[0][1])
            importances = [float(x) for x in self.rf_model.feature_importances_]
            engine = "random_forest"
        else:
            # Transparent deterministic fallback: same weighted formula documented in the model card.
            prob = min(0.99, max(0.01,
                0.25 * min(1, row["new_cases"] / 150) + 0.20 * min(1, max(0, row["cases_growth_rate"]) / 2.5)
                + 0.20 * (1 - min(1, max(0, row["vaccination_coverage"]))) + 0.15 * min(1, row["affected_animals"] / 1000)
                + 0.10 * min(1, row["animal_density"] / 500) + 0.05 * min(1, row["temperature"] / 42) + 0.05 * min(1, row["humidity"] / 95)))
            importances = [0.0, 0.15, 0.25, 0.0, 0.20, 0.05, 0.0, 0.05, 0.10, 0.0, 0.20]
            engine = "deterministic_fallback"

        risk_score = round(prob * 100, 1)
        level = "High Risk" if prob >= thresholds["high"] else ("Moderate Risk" if prob >= thresholds["moderate"] else "Low Risk")
        cgr = row["cases_growth_rate"]
        factors = sorted(({"factor": c.replace("_", " ").title(), "impact": round(importances[i], 3), "value": row[c]} for i, c in enumerate(FEATURE_COLS)), key=lambda x: -x["impact"])[:4]
        actions: List[str] = []
        if level == "High Risk":
            actions += ["Request veterinary field verification", "Consider movement restrictions pending verification"]
        if row["vaccination_coverage"] < 0.6:
            actions.append("Review vaccination coverage; consider targeted campaign")
        if cgr > 0.3:
            actions.append("Heighten active syndromic surveillance")
        if not actions:
            actions = ["Maintain routine clinical monitoring"]
        horizon = int(data.get("time_range")) if str(data.get("time_range", "")).isdigit() else 14
        info = self.model_info()
        return {
            "status": "OK",
            "disease": data.get("disease"),
            "district": data.get("district"),
            "risk_score": risk_score,
            "probability": round(prob, 3),
            "risk_level": level,
            # A model-agnostic confidence: distance from the decision boundary, not accuracy.
            "confidence": round(min(1.0, abs(prob - thresholds["high"]) * 2 + 0.5), 2),
            "confidence_basis": "distance from decision threshold (not validated accuracy)",
            "trend": "Increasing" if cgr > 0.1 else ("Stable" if cgr > -0.1 else "Decreasing"),
            "predicted_cases": None,
            "prediction_horizon_days": horizon,
            "top_risk_factors": factors,
            "evidence": {"features": row},
            "recommended_actions": actions,
            "model_version": info["model_version"],
            "engine": engine,
            "model": info,
            "label": PREDICTION_LABEL,
            "is_confirmed_diagnosis": False,
            "data_source_label": "MODEL PREDICTION (synthetic-trained, not validated)",
        }

    def detect_outbreak(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anomaly score for a single district's recent indicators (decision support only)."""
        new_cases = float(data.get("new_cases", 0))
        growth = float(data.get("cases_growth_rate", 0))
        deaths = float(data.get("deaths", 0))
        if self.iso_model is not None:
            import pandas as pd
            df = pd.DataFrame([{"new_cases": new_cases, "cases_growth_rate": growth, "deaths": deaths}])
            is_anomaly = bool(self.iso_model.predict(df)[0] == -1)
            score = float(self.iso_model.decision_function(df)[0])
            engine = "isolation_forest"
        else:
            is_anomaly = new_cases > 50 or deaths > 5 or growth > 0.5
            score = -0.25 if is_anomaly else 0.15
            engine = "threshold_rules"
        severity = ("High" if score < -0.1 or deaths > 3 else "Moderate") if is_anomaly else "Normal"
        return {
            "outbreak_detected": is_anomaly, "severity": severity, "anomaly_score": round(score, 3), "case_growth": growth,
            "affected_districts": [data.get("district")] if is_anomaly else [], "source": "backend", "engine": engine,
            "label": "PREDICTED RISK — requires field verification", "model_version": self.model_info()["model_version"],
        }

    def forecast(self, historical_cases: List[float], horizon: int = 14) -> Dict[str, Any]:
        """Damped-trend forecast with residual-based intervals. Refuses short series."""
        series = [float(x) for x in (historical_cases or []) if x is not None and x >= 0]
        horizon = max(1, min(int(horizon), 60))
        base = {"source": "backend", "provider": "damped_trend_baseline", "model_version": "damped-trend-1",
                "forecast_horizon_days": horizon, "training_points": len(series), "label": "FORECAST — statistical baseline, not validated"}
        if len(series) < MIN_FORECAST_POINTS:
            return {**base, "status": "INSUFFICIENT_DATA", "forecast": [], "message": f"At least {MIN_FORECAST_POINTS} historical points are required; got {len(series)}."}
        n = len(series)
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(series) / n
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, series, strict=True)) / max(1e-9, sum((x - mx) ** 2 for x in xs))
        intercept = my - slope * mx
        resid = [y - (intercept + slope * x) for x, y in zip(xs, series, strict=True)]
        sigma = math.sqrt(sum(r * r for r in resid) / max(1, n - 2))
        last, today, out = series[-1], datetime.utcnow(), []
        level = last
        for i in range(horizon):
            level = max(0.0, level + slope * (0.9 ** i))
            width = 1.96 * sigma * math.sqrt(1 + (i + 1) / n)
            out.append({"date": (today + timedelta(days=i + 1)).strftime("%Y-%m-%d"), "predicted_cases": int(round(level)),
                        "lower": max(0, int(round(level - width))), "upper": int(round(level + width))})
        return {**base, "status": "OK", "forecast": out, "confidence_interval": 0.95}


ml_service = MLService()
