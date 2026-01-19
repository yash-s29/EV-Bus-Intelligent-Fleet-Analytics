import os
import joblib
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pymongo.errors import PyMongoError

from db.mongo import maintenance_health

# =========================================================
# PATHS & MODEL LOADING
# =========================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # backend/
SOH_MODEL_PATH = os.path.join(BASE_DIR, "ml", "models", "soh_forecast.pkl")

_SOH_MODEL = None

def get_soh_model():
    """
    Lazy-load SOH model safely.
    """
    global _SOH_MODEL
    if _SOH_MODEL is not None:
        return _SOH_MODEL

    try:
        _SOH_MODEL = joblib.load(SOH_MODEL_PATH)
        print(f"✅ SOH model loaded from {SOH_MODEL_PATH}")
        return _SOH_MODEL
    except Exception as e:
        print(f"❌ SOH model unavailable: {e}")
        return None


# =========================================================
# CORE DOMAIN LOGIC
# =========================================================
def compute_status(soh_percent: float) -> str:
    """
    Canonical maintenance status.
    """
    if soh_percent < 60:
        return "Critical"
    elif soh_percent < 80:
        return "Warning"
    return "Healthy"

def estimate_next_service(soh_percent: float) -> str:
    """
    Determine next service date based on SOH.
    """
    if soh_percent < 60:
        days = 7
    elif soh_percent < 80:
        days = 30
    else:
        days = 90
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")


# =========================================================
# SINGLE BUS PREDICTION
# =========================================================
def predict_maintenance_for_bus(
    bus_id: str,
    features: List[float],
    last_service: str | None = None
) -> Dict[str, Any]:
    """
    Predict maintenance health for a single bus and persist.
    """
    if not bus_id:
        return {"error": "bus_id is required"}
    if not isinstance(features, list) or not features:
        return {"error": "features must be a non-empty list"}

    model = get_soh_model()
    if model is None:
        return {"error": "SOH model not available"}

    try:
        X = np.array([features], dtype=float)
        soh = float(model.predict(X)[0])
        soh = max(0.0, min(1.0, soh))
        soh_percent = round(soh * 100, 2)
        status = compute_status(soh_percent)

        record = {
            "bus_id": bus_id,
            "current_soh": soh_percent,
            "degradation_score": round(1 - soh, 4),
            "predicted_rul": int(soh_percent * 1.2),
            "status": status,
            "last_service": last_service or "Unknown",
            "next_service": estimate_next_service(soh_percent),
            "updated_at": datetime.utcnow()
        }

        # Persist to MongoDB
        maintenance_health.update_one(
            {"bus_id": bus_id},
            {"$set": record},
            upsert=True
        )

        return record

    except PyMongoError as e:
        return {"error": f"Database error: {e}"}
    except Exception as e:
        return {"error": f"Prediction failed: {e}"}


# =========================================================
# DASHBOARD AGGREGATION
# =========================================================
def get_maintenance_analytics() -> Dict[str, Any]:
    """
    Fleet-level analytics for dashboard consumption.
    """
    try:
        records = list(maintenance_health.find({}, {"_id": 0}))

        if not records:
            return {
                "upcoming_services": 0,
                "active_alerts": 0,
                "avg_battery_health": None,
                "records": []
            }

        upcoming = 0
        alerts = 0
        soh_values = []
        normalized_records = []

        for r in records:
            soh = r.get("current_soh")
            if not isinstance(soh, (int, float)):
                continue

            status = compute_status(soh)
            if status in ("Warning", "Critical"):
                upcoming += 1
            if status == "Critical":
                alerts += 1

            soh_values.append(soh)

            normalized_records.append({
                "bus_id": r.get("bus_id"),
                "last_service": r.get("last_service", "—"),
                "next_service": r.get("next_service", "—"),
                "status": status,
                "current_soh": soh,
                "predicted_rul": r.get("predicted_rul")
            })

        avg_soh = round(sum(soh_values) / len(soh_values), 2) if soh_values else None

        return {
            "upcoming_services": upcoming,
            "active_alerts": alerts,
            "avg_battery_health": avg_soh,
            "records": normalized_records
        }

    except PyMongoError as e:
        return {"error": f"Database aggregation failed: {e}"}
