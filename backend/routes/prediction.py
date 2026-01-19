import os
import sys
from flask import Blueprint, request, jsonify

# =========================================================
# 1. PATH RESOLUTION
# =========================================================
# Ensures 'backend' is the root for imports regardless of entry point
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# =========================================================
# 2. SAFE IMPORT
# =========================================================
try:
    # This links directly to your prediction_service logic
    from services.prediction_service import predict_trip
except ImportError as e:
    print(f"❌ [Critical Import Error] Prediction Blueprint: {e}")
    predict_trip = None

# =========================================================
# 3. BLUEPRINT CONFIGURATION
# =========================================================
# URL Prefix: /api/prediction -> endpoint will be /api/prediction/predict
prediction_bp = Blueprint("prediction", __name__, url_prefix="/api/prediction")

@prediction_bp.route("/predict", methods=["POST"])
def predict():
    """
    Primary API endpoint for EV Trip Predictions.
    Receives JSON from frontend -> Validates -> Executes AI Service -> Returns JSON.
    """
    
    # A. Initial Payload Validation
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "success": False, 
            "error": "Malformed request. Please ensure Content-Type is application/json."
        }), 400

    # B. Field Extraction
    route_id = data.get("route_id")
    passenger_load = data.get("passenger_load")
    weather = data.get("weather")
    # Current SoC defaults to 95.0 if the bus doesn't report it
    current_soc = data.get("current_soc", 95.0)  
    bus_id = data.get("bus_id", "EV-COMMANDER-01")

    # C. Required Field Guard
    if not route_id or passenger_load is None or not weather:
        return jsonify({
            "success": False,
            "error": "Required data points (route_id, load, weather) are missing."
        }), 400

    # D. Data Sanitization & Logical Bounds
    try:
        p_load = float(passenger_load)
        c_soc = float(current_soc)
        
        # Prevent physical impossibilities (SoC > 100% or < 0%)
        if not (0 <= p_load <= 100):
            return jsonify({"success": False, "error": "Passenger load must be between 0 and 100."}), 400
        if not (0 <= c_soc <= 100):
            return jsonify({"success": False, "error": "Battery SoC must be between 0 and 100."}), 400

        sanitized_data = {
            "route_id": str(route_id),
            "passenger_load": p_load,
            "weather": str(weather).lower().strip(),
            "current_soc": c_soc,
            "bus_id": str(bus_id)
        }
        
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Passenger load and SoC must be numeric values."}), 400

    # E. Service Execution Guard
    if predict_trip is None:
        return jsonify({
            "success": False, 
            "error": "AI Prediction Service is offline. Check server initialization logs."
        }), 503

    # F. Execution & Response Generation
    try:
        # Calls prediction_service.py -> AI Engine -> DB Save
        result = predict_trip(sanitized_data)
        
        # Return standardized structure for the frontend prediction.js
        return jsonify({
            "success": True,
            "data": {
                "bus_id": result.get("bus_id"),
                "route_id": result.get("route_id"),
                "predicted_end_soc": result.get("predicted_end_soc"),
                "predicted_soh": result.get("predicted_soh"), 
                "risk_level": result.get("risk_level"),
                "recommended_speed": result.get("recommended_speed"),
                "energy_curve": result.get("energy_curve", []),
                "weather": sanitized_data['weather'],
                "timestamp": result.get("timestamp")
            }
        }), 200

    except Exception as e:
        print(f"❌ [API Error] Prediction failed: {str(e)}")
        return jsonify({
            "success": False, 
            "error": "The AI engine encountered an internal calculation error.",
            "details": str(e)
        }), 500