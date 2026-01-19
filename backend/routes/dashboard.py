from flask import Blueprint, jsonify
import time
from services.dashboard_service import get_dashboard_metrics

# -----------------------------
# Blueprint Configuration
# -----------------------------
dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

@dashboard_bp.route("/kpis", methods=["GET"])
def dashboard_metrics():
    """
    Primary API Endpoint. 
    Now includes Sustainability (CO2) metrics for corporate reporting.
    """
    try:
        # 1️⃣ Fetch processed data from the service layer
        # The service layer now calculates 'co2_savings' based on fleet energy
        metrics = get_dashboard_metrics() or {}

        # 2️⃣ Build a high-integrity response
        # Using .get() with defaults prevents frontend crashes on empty data
        response_data = {
            # Operational KPIs
            "avg_soc": round(float(metrics.get("avg_soc", 0.0)), 1),
            "avg_soh": round(float(metrics.get("avg_soh", 0.0)), 1),
            "total_energy": round(float(metrics.get("total_energy", 0.0)), 2),
            "fleet_readiness": int(metrics.get("fleet_readiness", 0)),
            
            # Sustainability / Green Metrics
            "co2_savings": round(float(metrics.get("co2_savings", 0.0)), 2),
            
            # Distribution & Visuals
            "status_counts": metrics.get("status_counts", {
                "active": 0, "charging": 0, "idle": 0, "critical": 0
            }),
            
            # Real-time lists
            "alerts": metrics.get("alerts", []),
            "energy_history": metrics.get("energy_history", [])
        }

        # 3️⃣ Professional Console Logging
        # Keeps track of both operational readiness and environmental impact
        print(f"🌍 [DASHBOARD] Sync: {response_data['fleet_readiness']}% Ready | "
              f"🌱 {response_data['co2_savings']}kg CO2 Saved")

        # 4️⃣ Successful Response
        return jsonify({
            "success": True,
            "data": response_data,
            "server_time": int(time.time())
        }), 200

    except Exception as e:
        # Structured error response to prevent frontend "spinning" states
        print(f"❌ [API ERROR] Dashboard Route Crash: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Operational data currently unavailable",
            "details": str(e)
        }), 500