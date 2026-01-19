# logs.py
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import csv
import io
import logging
from typing import Optional, List, Dict

from services.fleet_service import get_fleet_logs, get_telemetry_for_csv

# -----------------------------
# Blueprint
# -----------------------------
logs_bp = Blueprint("logs", __name__, url_prefix="/api/logs")

# -----------------------------
# Logging
# -----------------------------
logger = logging.getLogger("logs")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# -----------------------------
# Helper: parse ISO date safely
# -----------------------------
def parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return None

# -----------------------------
# Normalize telemetry/fleet record
# -----------------------------
def normalize_record(rec: Dict) -> Dict:
    """
    Safely normalize telemetry/fleet fields for CSV or JSON.
    Missing/None values replaced with safe defaults.
    """
    def safe_float(val, default=0.0):
        try:
            return round(float(val), 6) if val is not None else default
        except (ValueError, TypeError):
            return default

    return {
        "bus_id": rec.get("bus_id", "--"),
        "timestamp": rec.get("timestamp").isoformat() if isinstance(rec.get("timestamp"), datetime) else rec.get("timestamp", ""),
        "soc": safe_float(rec.get("soc")),
        "soh": safe_float(rec.get("soh") or rec.get("predicted_soh")),
        "terminal_voltage": safe_float(rec.get("terminal_voltage")),
        "battery_current": safe_float(rec.get("battery_current")),
        "battery_temp": safe_float(rec.get("battery_temp")),
        "ambient_temp": safe_float(rec.get("ambient_temp")),
        "internal_resistance": safe_float(rec.get("internal_resistance")),
        "action_current": safe_float(rec.get("action_current")),
        "action_voltage": safe_float(rec.get("action_voltage")),
        "dT_dt": safe_float(rec.get("dT_dt")),
        "dV_dt": safe_float(rec.get("dV_dt")),
        "soc_delta": safe_float(rec.get("soc_delta")),
        "thermal_stress_index": safe_float(rec.get("thermal_stress_index")),
        "aging_indicator": safe_float(rec.get("aging_indicator")),
        "charging_efficiency": safe_float(rec.get("charging_efficiency")),
        "charging_time": safe_float(rec.get("charging_time")),
        "cycle_degradation": safe_float(rec.get("cycle_degradation")),
        "over_temp_flag": rec.get("over_temp_flag", 0),
        "over_voltage_flag": rec.get("over_voltage_flag", 0),
        "balancing_time": safe_float(rec.get("balancing_time")),
        "hour": rec.get("hour", 0),
        "dayofweek": rec.get("dayofweek", 0),
        "maintenance_due": rec.get("maintenance_due") or "",
        "issues": rec.get("issues", 0),
        "status": rec.get("status", "--")
    }

# -----------------------------
# GET /api/logs
# -----------------------------
@logs_bp.route("/", methods=["GET"])
def fleet_logs():
    """
    Fetch fleet logs (SOH, maintenance, telemetry) for a bus.
    Query params: bus_id, limit, start, end, export (CSV)
    """
    bus_id: Optional[str] = request.args.get("bus_id")
    limit: int = min(max(request.args.get("limit", 100, type=int), 1), 1000)
    export_csv: bool = request.args.get("export", "false").lower() == "true"
    start_dt: Optional[datetime] = parse_iso_date(request.args.get("start"))
    end_dt: Optional[datetime] = parse_iso_date(request.args.get("end"))

    if request.args.get("start") and not start_dt:
        return jsonify(success=False, error="Invalid start date. Use YYYY-MM-DD"), 400
    if request.args.get("end") and not end_dt:
        return jsonify(success=False, error="Invalid end date. Use YYYY-MM-DD"), 400
    if start_dt and end_dt and start_dt > end_dt:
        return jsonify(success=False, error="Start date cannot be after end date"), 400

    try:
        # -----------------------------
        # CSV export
        # -----------------------------
        if export_csv:
            if not bus_id:
                return jsonify(success=False, error="bus_id is required for CSV export"), 400

            telemetry_records: List[Dict] = get_telemetry_for_csv(
                bus_id=bus_id,
                limit=limit,
                start=start_dt,
                end=end_dt
            )

            if not telemetry_records:
                return jsonify(success=False, error="No telemetry data found"), 404

            telemetry_records = [normalize_record(rec) for rec in telemetry_records]

            output = io.StringIO()
            fieldnames = list(telemetry_records[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(telemetry_records)

            output.seek(0)
            filename = f"{bus_id}_telemetry_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
            logger.info(f"CSV telemetry export generated for bus '{bus_id}'")
            return Response(
                output.getvalue(),
                mimetype="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )

        # -----------------------------
        # JSON → Fleet Logs summary
        # -----------------------------
        records: List[Dict] = get_fleet_logs(
            bus_id=bus_id,
            limit=limit,
            start=start_dt,
            end=end_dt
        )

        if not records:
            logger.info(f"No fleet summary records found for bus '{bus_id or 'ALL'}'")
            return jsonify(success=True, data={"bus_id": bus_id, "count": 0, "records": []}), 200

        # Calculate status & issues if not present
        for rec in records:
            soh_percent = rec.get("soh") or rec.get("predicted_soh") or 0
            if soh_percent <= 1:
                soh_percent *= 100
            soh_percent = round(float(soh_percent), 1)

            # derive status and issues
            if soh_percent >= 90:
                rec["status"] = "Good"
                rec["issues"] = 0
            elif soh_percent >= 60:
                rec["status"] = "Proper"
                rec["issues"] = 0
            elif soh_percent >= 50:
                rec["status"] = "Attention"
                rec["issues"] = 1
            else:
                rec["status"] = "Critical"
                rec["issues"] = 1

        records = [normalize_record(rec) for rec in records]

        logger.info(f"Fetched {len(records)} fleet summary records for bus '{bus_id or 'ALL'}'")
        return jsonify(
            success=True,
            data={
                "bus_id": bus_id,
                "limit": limit,
                "count": len(records),
                "records": records
            }
        ), 200

    except Exception as e:
        logger.error(f"Failed to fetch fleet logs for bus '{bus_id or 'ALL'}': {e}", exc_info=True)
        return jsonify(success=False, error="Failed to fetch fleet logs"), 500
