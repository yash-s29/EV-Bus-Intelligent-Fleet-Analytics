# services/fleet_service.py
from datetime import datetime
from typing import List, Dict, Any, Optional
from db.mongo import maintenance_health, telemetry_logs  # MongoDB collections
from pymongo.errors import PyMongoError

# -----------------------------
# SOH Thresholds → Status & Issues
# -----------------------------
def compute_status_and_issues(soh: float) -> Dict[str, Any]:
    """
    Maps predicted SOH to Status & # Issues based on thresholds.
    soh: 0-100 percentage
    Returns:
        {"status": str, "issues_count": int}
    """
    if soh >= 90:
        return {"status": "Good", "issues_count": 0}
    elif 60 <= soh < 90:
        return {"status": "Proper", "issues_count": 0}
    elif 50 <= soh < 60:
        return {"status": "Attention", "issues_count": 1}
    else:  # soh < 50
        return {"status": "Critical", "issues_count": 1}

# -----------------------------
# Fetch fleet logs summary (for table)
# -----------------------------
def get_fleet_logs(
    bus_id: Optional[str] = None,
    limit: int = 100,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Fetches fleet logs (SOH & maintenance) from maintenance_health collection.
    Returns summary rows for frontend table:
        - bus_id
        - predicted_soh (%)
        - maintenance_due (human-readable)
        - issues_count (derived)
        - status (derived)
        - issues (original array for click-to-alert)
    """
    query: Dict[str, Any] = {}
    if bus_id:
        query["bus_id"] = bus_id

    if start and end:
        query["maintenance_due"] = {"$gte": start, "$lte": end}
    elif start:
        query["maintenance_due"] = {"$gte": start}
    elif end:
        query["maintenance_due"] = {"$lte": end}

    try:
        records = list(
            maintenance_health.find(query, {"_id": 0})
            .sort("maintenance_due", -1)
            .limit(limit)
        )
    except PyMongoError as e:
        raise RuntimeError(f"Failed to fetch fleet logs: {e}")

    # Enrich each record
    for r in records:
        # Convert SOH to percentage
        soh = float(r.get("predicted_soh", 0.0)) * 100
        r["predicted_soh"] = round(soh, 1)

        # Format maintenance_due
        if "maintenance_due" in r and isinstance(r["maintenance_due"], datetime):
            r["maintenance_due"] = r["maintenance_due"].strftime("%Y-%m-%d %H:%M:%S")
        else:
            r["maintenance_due"] = "--"

        # Keep original issues for click-to-alert
        r["issues"] = r.get("issues", [])
        # Compute derived status & issues_count
        derived = compute_status_and_issues(soh)
        r["status"] = derived["status"]
        r["issues_count"] = derived["issues_count"]

    return records

# -----------------------------
# Fetch raw telemetry for CSV export
# -----------------------------
def get_telemetry_for_csv(
    bus_id: str,
    limit: int = 1000,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Fetch raw telemetry from telemetry_logs collection.
    Returns all fields for CSV export.
    The limit prevents huge exports from freezing the browser.
    """
    if not bus_id:
        raise ValueError("bus_id is required for telemetry export")

    query: Dict[str, Any] = {"bus_id": bus_id}

    if start and end:
        query["timestamp"] = {"$gte": start, "$lte": end}
    elif start:
        query["timestamp"] = {"$gte": start}
    elif end:
        query["timestamp"] = {"$lte": end}

    try:
        records = list(
            telemetry_logs.find(query, {"_id": 0})
            .sort("timestamp", -1)
            .limit(limit)
        )
    except PyMongoError as e:
        raise RuntimeError(f"Failed to fetch telemetry for CSV: {e}")

    # Convert numeric fields to float for consistency
    numeric_fields = [
        "soc", "predicted_soh", "voltage", "current", "temperature",
        "ambient_temperature", "internal_resistance", "action_current", "action_voltage"
    ]
    for r in records:
        for field in numeric_fields:
            if field in r:
                try:
                    r[field] = float(r[field])
                except Exception:
                    r[field] = 0.0

        # Add derived status & issues_count per SOH
        soh = float(r.get("predicted_soh", 0.0)) * 100 if "predicted_soh" in r else 0.0
        derived = compute_status_and_issues(soh)
        r["status"] = derived["status"]
        r["issues_count"] = derived["issues_count"]

    return records
