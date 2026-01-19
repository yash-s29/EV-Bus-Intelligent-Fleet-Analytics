import os
import sys
from datetime import datetime

# =========================================================
# 1. PATH INJECTION
# =========================================================
# Ensures that the service can find the 'db' and 'ml' modules in the parent directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# =========================================================
# 2. ENGINE INITIALIZATION
# =========================================================
try:
    from db.mongo import trip_predictions
    from ml.predictors import EVPredictor
    
    # Initialize the high-performance ML predictor
    predictor = EVPredictor()
    print("✅ Prediction Engine Initialized successfully.")
except Exception as e:
    print(f"❌ [Critical Error] Service Init Failed: {e}")
    predictor = None
    trip_predictions = None

def predict_trip(input_payload: dict) -> dict:
    """
    Orchestrates the prediction logic: 
    Inputs -> ML Inference -> SOH Calculation -> DB Save -> Result
    """
    if predictor is None:
        raise RuntimeError("Prediction Engine is not initialized. Check ML model paths.")

    try:
        # 1. Sanitize & Extract Inputs from API payload
        passengers = float(input_payload.get("passenger_load", 0))
        current_soc = float(input_payload.get("current_soc", 95.0))
        weather = str(input_payload.get("weather", "normal")).lower().strip()
        bus_id = input_payload.get("bus_id", "EV-COMMANDER")
        route_id = input_payload.get("route_id", "R-001")
        
        # 2. Dynamic Feature Mapping
        # We adjust variables based on environment to provide realistic ML input
        distance = 45.0  # Default route distance in km
        avg_speed = 55.0  # Standard speed
        
        # Adjust speed for adverse weather conditions
        if weather in ["hot", "cold", "extreme heat", "extreme cold", "rainy"]:
            avg_speed = 42.0

        trip_features = {
            "start_soc": current_soc,
            "route_distance_km": distance,
            "avg_speed_kmph": avg_speed,
            "passenger_load": passengers
        }

        # 3. Perform ML Predictions
        # A. Feasibility and Battery Drain (End SoC)
        trip_res = predictor.predict_trip_feasibility(trip_features)
        
        # B. Battery Health Impact (SOH)
        # SOH impact is calculated based on Depth of Discharge (DoD)
        dod = current_soc - trip_res["predicted_end_soc"]
        soh_features = {
            "battery_cycles": 120, # Simulated cycle count
            "avg_depth_of_discharge": dod,
            "temperature_variance": 12.0 if weather != "normal" else 4.0
        }
        soh_res = predictor.predict_soh(soh_features)

        # 4. Construct Final Response Payload
        # Values are rounded for clean UI display
        result = {
            "bus_id": bus_id,
            "route_id": route_id,
            "predicted_end_soc": round(trip_res["predicted_end_soc"], 2),
            "predicted_soh": round(soh_res["predicted_soh"], 2),
            "risk_level": trip_res["risk_level"],
            "recommended_speed": 40 if trip_res["risk_level"] == "CRITICAL" else 60,
            "energy_curve": trip_res["energy_curve"],
            "weather": weather,
            "timestamp": datetime.utcnow().isoformat()
        }

        # 5. Database Persistence
        # Store a copy in MongoDB for fleet history
        if trip_predictions is not None:
            db_entry = result.copy()
            trip_predictions.insert_one(db_entry)
            
            # Ensure the MongoDB ObjectId doesn't break JSON serialization
            if "_id" in result: 
                result.pop("_id")

        return result

    except Exception as e:
        print(f"❌ [Service Error]: {str(e)}")
        raise e