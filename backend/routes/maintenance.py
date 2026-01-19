from flask import Blueprint, jsonify

# =========================================================
# SERVICE LAYER IMPORT
# =========================================================
try:
    from services.maintenance_service import get_maintenance_analytics
except ImportError as e:
    print(f"❌ Maintenance service import failed: {e}")
    get_maintenance_analytics = None

# =========================================================
# BLUEPRINT SETUP
# =========================================================
maintenance_bp = Blueprint(
    "maintenance",
    __name__,
    url_prefix="/api/maintenance"
)

# =========================================================
# ROUTES
# =========================================================
@maintenance_bp.route("", methods=["GET"])
def get_maintenance_overview():
    """
    Unified API for Maintenance Analytics Dashboard.
    Returns KPIs + normalized maintenance records.
    """
    if get_maintenance_analytics is None:
        return jsonify({
            "success": False,
            "error": "Maintenance service unavailable"
        }), 503

    try:
        analytics = get_maintenance_analytics()

        if not isinstance(analytics, dict):
            return jsonify({
                "success": False,
                "error": "Invalid maintenance analytics response"
            }), 500

        if "error" in analytics:
            return jsonify({
                "success": False,
                "error": analytics["error"]
            }), 500

        # 🔒 HARD-LOCKED RESPONSE CONTRACT FOR FRONTEND
        response = {
            "success": True,
            "data": {
                "upcoming_services": int(analytics.get("upcoming_services", 0)),
                "active_alerts": int(analytics.get("active_alerts", 0)),
                "avg_battery_health": (
                    float(analytics["avg_battery_health"])
                    if analytics.get("avg_battery_health") is not None else None
                ),
                "records": analytics.get("records", [])
            }
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"❌ Maintenance API error: {e}")
        return jsonify({
            "success": False,
            "error": "Internal server error while generating maintenance analytics"
        }), 500

# =========================================================
# HEALTH CHECK ENDPOINT
# =========================================================
@maintenance_bp.route("/health", methods=["GET"])
def maintenance_health_check():
    """
    Lightweight health probe for monitoring & debug.
    """
    return jsonify({
        "success": True,
        "service": "maintenance",
        "status": "ok"
    }), 200
