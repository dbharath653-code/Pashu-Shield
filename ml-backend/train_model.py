"""
Train the outbreak-risk model and write a verifiable model card.

Data sources
------------
  --data PATH.csv   Authorised real dataset (preferred). Required columns: FEATURE_COLS,
                    `outbreak_risk` (0/1 label), `observed_at` (ISO date), `district`.
                    Split is TEMPORAL (train on the past, test on the most recent 20%) to avoid
                    leakage; exact duplicate rows are removed before splitting.
  (no --data)       Generates a SYNTHETIC development dataset. The resulting model card is
                    labelled training_data_type=SYNTHETIC / validation_status=NOT_VALIDATED_SYNTHETIC
                    and must not be used as evidence of real-world performance.

Outputs (ml-backend/models/): rf_model.pkl, scaler.pkl, iso_model.pkl, model_card.json with
SHA-256 checksums that the backend verifies before unpickling.
"""
import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.preprocessing import StandardScaler

MODELS_DIR = Path(__file__).resolve().parent / "models"
FEATURE_COLS = ["animal_population", "affected_animals", "new_cases", "deaths", "vaccination_coverage", "temperature",
                "rainfall", "humidity", "animal_density", "previous_cases", "cases_growth_rate"]


def synthetic(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "district": rng.choice(["Pune", "Satara", "Nashik", "Nagpur", "Solapur", "Kolhapur"], n),
        "animal_population": rng.integers(500, 50000, n), "affected_animals": rng.integers(0, 1000, n),
        "new_cases": rng.integers(0, 150, n), "deaths": rng.integers(0, 50, n),
        "vaccination_coverage": rng.uniform(0.1, 0.95, n), "temperature": rng.uniform(20.0, 42.0, n),
        "rainfall": rng.uniform(0.0, 200.0, n), "humidity": rng.uniform(30.0, 95.0, n),
        "animal_density": rng.uniform(10.0, 500.0, n), "previous_cases": rng.integers(0, 500, n),
        "cases_growth_rate": rng.uniform(-0.5, 2.5, n),
    })
    score = ((df.new_cases / 150) * 0.25 + (df.cases_growth_rate / 2.5) * 0.20 + (1 - df.vaccination_coverage) * 0.20
             + (df.affected_animals / 1000) * 0.15 + (df.animal_density / 500) * 0.10 + (df.temperature / 42) * 0.05 + (df.humidity / 95) * 0.05)
    score = np.clip(score + rng.normal(0, 0.05, n), 0, 1)
    df["outbreak_risk"] = (score > 0.5).astype(int)
    start = datetime(2024, 1, 1)
    df["observed_at"] = [start + timedelta(hours=int(h)) for h in sorted(rng.integers(0, 24 * 700, n))]
    return df


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="CSV of authorised real surveillance data")
    ap.add_argument("--dataset-name", default=None)
    args = ap.parse_args()

    if args.data:
        df = pd.read_csv(args.data, parse_dates=["observed_at"])
        missing = [c for c in FEATURE_COLS + ["outbreak_risk", "observed_at"] if c not in df.columns]
        if missing:
            raise SystemExit(f"dataset missing columns: {missing}")
        data_type, dataset = "REAL", args.dataset_name or Path(args.data).name
    else:
        print("WARNING: no --data given; training on SYNTHETIC development data.")
        df, data_type, dataset = synthetic(), "SYNTHETIC", "synthetic-dev-v1 (generated, seed=42)"

    before = len(df)
    df = df.dropna(subset=FEATURE_COLS + ["outbreak_risk"]).drop_duplicates(subset=FEATURE_COLS + ["observed_at"])
    df = df.sort_values("observed_at").reset_index(drop=True)
    cut = int(len(df) * 0.8)
    train, test = df.iloc[:cut], df.iloc[cut:]
    scaler = StandardScaler().fit(train[FEATURE_COLS])
    rf = RandomForestClassifier(n_estimators=150, max_depth=10, class_weight="balanced", random_state=42)
    rf.fit(scaler.transform(train[FEATURE_COLS]), train.outbreak_risk)
    prob = rf.predict_proba(scaler.transform(test[FEATURE_COLS]))[:, 1]
    pred = (prob >= 0.6).astype(int)
    tn, fp, fn, tp = confusion_matrix(test.outbreak_risk, pred, labels=[0, 1]).ravel()
    metrics = {
        "accuracy": round(accuracy_score(test.outbreak_risk, pred), 3),
        "precision": round(precision_score(test.outbreak_risk, pred, zero_division=0), 3),
        "recall": round(recall_score(test.outbreak_risk, pred, zero_division=0), 3),
        "specificity": round(tn / max(1, tn + fp), 3),
        "f1_score": round(f1_score(test.outbreak_risk, pred, zero_division=0), 3),
        "roc_auc": round(roc_auc_score(test.outbreak_risk, prob), 3) if test.outbreak_risk.nunique() > 1 else None,
        "pr_auc": round(average_precision_score(test.outbreak_risk, prob), 3),
        "brier_score": round(brier_score_loss(test.outbreak_risk, prob), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "positive_rate_test": round(float(test.outbreak_risk.mean()), 3),
    }
    iso = IsolationForest(contamination=0.05, random_state=42).fit(train[["new_cases", "cases_growth_rate", "deaths"]])

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, MODELS_DIR / "rf_model.pkl")
    joblib.dump(scaler, MODELS_DIR / "scaler.pkl")
    joblib.dump(iso, MODELS_DIR / "iso_model.pkl")
    card = {
        "model_version": f"rf-{datetime.utcnow().strftime('%Y%m%d')}-{data_type.lower()}",
        "algorithm": "RandomForestClassifier (class_weight=balanced) + IsolationForest",
        "training_dataset": dataset,
        "training_data_type": data_type,
        "validation_status": "NOT_VALIDATED_SYNTHETIC" if data_type == "SYNTHETIC" else "TEMPORAL_HOLDOUT_ONLY — requires prospective field validation",
        "training_date": datetime.utcnow().isoformat(),
        "training_period": [str(train.observed_at.min()), str(train.observed_at.max())],
        "evaluation_split": {"method": "temporal 80/20", "test_period": [str(test.observed_at.min()), str(test.observed_at.max())]},
        "rows_before_cleaning": before, "training_samples": len(train), "test_samples": len(test),
        "features": FEATURE_COLS, "thresholds": {"high": 0.6, "moderate": 0.3},
        "metrics": metrics,
        "artifacts": {f: sha(MODELS_DIR / f) for f in ("rf_model.pkl", "scaler.pkl", "iso_model.pkl")},
    }
    (MODELS_DIR / "model_card.json").write_text(json.dumps(card, indent=2))
    legacy = MODELS_DIR / "metrics.json"
    if legacy.exists():
        legacy.unlink()
    print(json.dumps(card["metrics"], indent=2))


if __name__ == "__main__":
    main()
