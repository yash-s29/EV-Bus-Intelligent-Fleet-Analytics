from db.mongo import telemetry_logs
from datetime import datetime, timedelta

# -----------------------------
# Professional Fleet Thresholds
# -----------------------------
CRITICAL_SOH_THRESHOLD = 0.7  # 70% State of Health
LOW_SOC_THRESHOLD = 20.0      # 20% State of Charge

# -----------------------------
# Sustainability Constants
# -----------------------------
# Avg. CO2 emitted by a Diesel Bus: ~1.3 kg/km
# Avg. CO2 emitted by an EV (Grid-based): ~0.5 kg/km
# NET SAVINGS = 0.8 kg per km traveled
CO2_SAVINGS_PER_KM = 0.8 
AVG_KWH_PER_KM = 1.2 # Average energy consumption of an electric bus

def get_dashboard_metrics():
    """
    Core engine with Sustainability Metrics & MongoDB Schema Compatibility.
    Calculates KPIs, CO2 Abatement, and Time-series data.
    """
    metrics = {
        "avg_soc": 0.0,
        "avg_soh": 0.0,
        "total_energy": 0.0,
        "co2_savings": 0.0,  # New Sustainability Metric
        "fleet_readiness": 0, 
        "status_counts": {"active": 0, "charging": 0, "idle": 0, "critical": 0},
        "alerts": [],
        "energy_history": []
    }

    try:
        # 1. AGGREGATION: Get latest state per bus
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$bus_id",
                "bus_id": {"$first": "$bus_id"},
                "SOC": {"$first": "$SOC"},
                "SOH": {"$first": "$SOH"},
                "energy": {"$first": "$terminal_voltage"},
                "timestamp": {"$first": "$timestamp"}
            }}
        ]

        latest_logs = list(telemetry_logs.aggregate(pipeline))
        total_buses = len(latest_logs)

        if total_buses > 0:
            soc_total = 0.0
            soh_total = 0.0
            energy_sum = 0.0
            ready_count = 0

            for log in latest_logs:
                # --- SCHEMA ALIGNMENT ---
                # Multiplying SOC by 10 to normalize your decimal data (e.g. 1.1 -> 11%)
                soc = (float(log.get("SOC") or 0.0) * 10) 
                soh = float(log.get("SOH") or 0.0)
                # Using terminal_voltage as a proxy for energy consumption
                energy = float(log.get("energy") or 0.0)
                bus_id = str(log.get("bus_id", "Unknown"))

                soc_total += soc
                soh_total += soh
                energy_sum += energy

                # --- OPERATIONAL LOGIC ---
                is_healthy = soh >= CRITICAL_SOH_THRESHOLD
                is_charged = soc >= LOW_SOC_THRESHOLD

                if is_healthy and is_charged:
                    ready_count += 1
                    metrics["status_counts"]["active"] += 1
                else:
                    metrics["status_counts"]["critical"] += 1
                    
                    # Generate Alerts
                    issue_msg = ""
                    if not is_healthy:
                        issue_msg = f"Battery Degradation ({round(soh * 100)}% SOH)"
                    elif not is_charged:
                        issue_msg = f"Low Charge ({round(soc, 1)}% SOC)"
                    
                    metrics["alerts"].append({
                        "bus_id": bus_id,
                        "issue": issue_msg or "Check Vehicle Status",
                        "level": "critical" if not is_healthy else "warning"
                    })

            # --- KPI FINAL CALCULATIONS ---
            metrics["avg_soc"] = round(soc_total / total_buses, 1)
            metrics["avg_soh"] = round((soh_total / total_buses) * 100, 1)
            metrics["total_energy"] = round(energy_sum, 2)
            metrics["fleet_readiness"] = int((ready_count / total_buses) * 100)

            # --- GREEN METRIC: CO2 SAVINGS ---
            # Formula: (Total Energy Used / Efficiency) * Savings per KM
            estimated_km = energy_sum / AVG_KWH_PER_KM
            metrics["co2_savings"] = round(estimated_km * CO2_SAVINGS_PER_KM, 2)

        # 2. TIME-SERIES: Energy history
        history_pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$limit": 12},
            {"$project": {
                "timestamp": 1,
                "energy": "$terminal_voltage"
            }},
            {"$sort": {"timestamp": 1}}
        ]
        
        history_cursor = list(telemetry_logs.aggregate(history_pipeline))
        
        for doc in history_cursor:
            ts = doc.get("timestamp")
            time_label = ts.strftime("%H:%M") if isinstance(ts, datetime) else "00:00"
            metrics["energy_history"].append({
                "timestamp": time_label,
                "value": round(float(doc.get("energy") or 0.0), 2)
            })

    except Exception as e:
        print(f"❌ Dashboard Service Failure: {str(e)}")

    return metrics