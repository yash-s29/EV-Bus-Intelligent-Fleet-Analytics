from flask import Blueprint, jsonify
from db.mongo import telemetry_logs, maintenance_health
from datetime import datetime
from typing import Dict, List
import random

route_bp = Blueprint("route", __name__)

BASE_LAT = 18.5204
BASE_LNG = 73.8567

SIM_GPS_STATE: Dict[str, Dict[str, float]] = {}

CHARGING_STATIONS = [
    {"name": "Station A", "lat": 18.525, "lng": 73.855},
    {"name": "Station B", "lat": 18.515, "lng": 73.865},
    {"name": "Station C", "lat": 18.530, "lng": 73.845},
]

def clamp(val: float, min_v: float, max_v: float) -> float:
    return max(min(val, max_v), min_v)

def normalize(val, decimals=2):
    try:
        return round(float(val), decimals)
    except Exception:
        return 0.0

def compute_status_from_soc(soc_pct: float) -> str:
    if soc_pct < 25:
        return "CRITICAL"
    elif soc_pct < 50:
        return "MEDIOCRE"
    else:
        return "GOOD"

def get_simulated_gps(bus_id: str):
    if bus_id not in SIM_GPS_STATE:
        SIM_GPS_STATE[bus_id] = {
            "lat": BASE_LAT + random.uniform(-0.015, 0.015),
            "lng": BASE_LNG + random.uniform(-0.015, 0.015),
        }
    else:
        SIM_GPS_STATE[bus_id]["lat"] += random.uniform(-0.0001, 0.0001)
        SIM_GPS_STATE[bus_id]["lng"] += random.uniform(-0.0001, 0.0001)
    return SIM_GPS_STATE[bus_id]

def nearest_charging(lat, lng):
    return min(
        CHARGING_STATIONS,
        key=lambda s: (s["lat"] - lat) ** 2 + (s["lng"] - lng) ** 2
    )

def generate_route_points(lat, lng, n=10):
    points = []
    for i in range(n):
        points.append([
            normalize(lat + random.uniform(-0.01, 0.01), 5),
            normalize(lng + random.uniform(-0.01, 0.01), 5)
        ])
    return points

@route_bp.route("/", methods=["GET"])
def route_status():
    try:
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$bus_id",
                "SOC": {"$first": "$SOC"},
                "timestamp": {"$first": "$timestamp"},
                "lat": {"$first": "$lat"},
                "lng": {"$first": "$lng"},
            }}
        ]
        telemetry = list(telemetry_logs.aggregate(pipeline))
        maintenance = {m["bus_id"]: m for m in maintenance_health.find({})}

        for i, t in enumerate(telemetry):
            if i % 3 == 0: t["SOC"] = random.uniform(0.05, 0.24)
            elif i % 3 == 1: t["SOC"] = random.uniform(0.25, 0.49)
            else: t["SOC"] = random.uniform(0.5, 1.0)

        buses: List[Dict] = []
        route_ids = ["Alpha-Line","Beta-Line","Gamma-Line","Delta-Line","Epsilon-Line"]

        for idx, t in enumerate(telemetry):
            bus_id = t["_id"]
            raw_soc = t.get("SOC", 0.0)
            soc_pct = normalize(raw_soc * 100, 1) if raw_soc <= 1.0 else normalize(min(raw_soc, 100.0), 1)
            status = compute_status_from_soc(soc_pct)

            lat, lng = t.get("lat"), t.get("lng")
            gps_simulated = False
            if lat is None or lng is None:
                gps = get_simulated_gps(bus_id)
                lat, lng = gps["lat"], gps["lng"]
                gps_simulated = True

            route_id = maintenance.get(bus_id, {}).get("route_id", route_ids[idx % len(route_ids)])
            route_points = generate_route_points(lat, lng, n=12)

            buses.append({
                "bus_id": bus_id,
                "route_id": route_id,
                "soc": soc_pct,
                "status": status,
                "lat": normalize(lat, 5),
                "lng": normalize(lng, 5),
                "gps_simulated": gps_simulated,
                "last_update": (
                    t["timestamp"].isoformat()
                    if isinstance(t.get("timestamp"), datetime)
                    else None
                ),
                "charging_station": (
                    nearest_charging(lat, lng) if status == "CRITICAL" else None
                ),
                "route_points": route_points
            })

        return jsonify({
            "success": True,
            "count": len(buses),
            "buses": buses
        }), 200

    except Exception as e:
        print(f"❌ route.py error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "buses": []
        }), 500
