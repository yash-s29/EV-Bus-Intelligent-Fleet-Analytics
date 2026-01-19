from datetime import datetime
from pymongo import ASCENDING, errors
from db.mongo import db

# =============================
# TELEMETRY LOGS (REAL SYSTEM)
# =============================

telemetry_schema = {
    "bus_id": str,

    # Time
    "timestamp": datetime,

    # Core battery state (RAW)
    "SOC": float,                     # 0.0 – 1.0 (normalized)
    "SOH": float,                     # 0.0 – 1.0
    "terminal_voltage": float,
    "battery_current": float,
    "battery_temp": float,
    "ambient_temp": float,

    # Derived physics
    "internal_resistance": float,
    "dT_dt": float,
    "dV_dt": float,
    "soc_delta": float,

    # ML + health indicators
    "thermal_stress_index": float,    # 0 – 1
    "aging_indicator": float,
    "cycle_degradation": float,

    # Safety flags
    "over_temp_flag": int,
    "over_voltage_flag": int,

    # Charging behavior
    "charging_efficiency": float,
    "charging_time": int,
    "balancing_time": float,

    # Context
    "hour": int,
    "dayofweek": int
}

try:
    db.telemetry_logs.create_index(
        [("bus_id", ASCENDING), ("timestamp", ASCENDING)],
        name="idx_bus_timestamp"
    )
except errors.PyMongoError as e:
    print(f"❌ Telemetry index error: {e}")

# =============================
# TRIP PREDICTIONS
# =============================

trip_prediction_schema = {
    "bus_id": str,
    "route_id": str,
    "predicted_end_soc": float,   # 0–100 %
    "predicted_soh": float,       # 0–1
    "risk_level": str,            # LOW | MEDIUM | HIGH
    "recommended_speed": float,
    "created_at": datetime
}

try:
    db.trip_predictions.create_index(
        [("bus_id", ASCENDING), ("route_id", ASCENDING), ("created_at", ASCENDING)],
        name="idx_trip_pred"
    )
except errors.PyMongoError as e:
    print(f"❌ Trip prediction index error: {e}")

# =============================
# MAINTENANCE HEALTH
# =============================

maintenance_schema = {
    "bus_id": str,
    "current_soh": float,
    "predicted_rul": int,
    "degradation_score": float,
    "updated_at": datetime
}

try:
    db.maintenance_health.create_index(
        "bus_id",
        unique=True,
        name="idx_maintenance_unique"
    )
except errors.PyMongoError as e:
    print(f"❌ Maintenance index error: {e}")

# =============================
# USERS
# =============================

user_schema = {
    "name": str,
    "email": str,
    "organization": str,
    "password_hash": str,
    "role": str,
    "is_active": bool,
    "created_at": datetime,
    "last_login": datetime
}

try:
    db.users.create_index(
        "email",
        unique=True,
        name="idx_user_email"
    )
except errors.PyMongoError as e:
    print(f"❌ User index error: {e}")
