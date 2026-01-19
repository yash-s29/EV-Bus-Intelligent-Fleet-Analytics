import streamlit as st
import pandas as pd
import joblib
from pathlib import Path

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="EV Battery AI",
    page_icon="⚡",
    layout="centered"
)

# =========================================================
# PATHS & SAFETY CHECKS
# =========================================================
BASE_DIR = Path(__file__).parent
MODEL_DIR = BASE_DIR / "ml" / "models"

SOC_MODEL_PATH = MODEL_DIR / "soc_rf.pkl"
SOH_MODEL_PATH = MODEL_DIR / "soh_lr.pkl"
SCALER_PATH    = MODEL_DIR / "scaler.pkl"

for path in [SOC_MODEL_PATH, SOH_MODEL_PATH, SCALER_PATH]:
    if not path.exists():
        st.error(f"❌ Missing model file: {path}")
        st.stop()

# =========================================================
# LOAD MODELS (CACHED)
# =========================================================
@st.cache_resource
def load_models():
    soc_model = joblib.load(SOC_MODEL_PATH)
    soh_model = joblib.load(SOH_MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    return soc_model, soh_model, scaler

soc_model, soh_model, scaler = load_models()

# =========================================================
# FEATURE CONTRACT (DO NOT CHANGE ORDER)
# =========================================================
MODEL_FEATURES = [
    "terminal_voltage", "battery_current", "battery_temp",
    "ambient_temp", "internal_resistance",
    "action_current", "action_voltage",
    "dT_dt", "dV_dt", "soc_delta",
    "thermal_stress_index", "aging_indicator",
    "charging_efficiency", "charging_time",
    "cycle_degradation",
    "over_temp_flag", "over_voltage_flag",
    "balancing_time",
    "hour", "dayofweek"
]

# =========================================================
# UI HEADER
# =========================================================
st.title("⚡ EV Battery Intelligence Dashboard")
st.caption("Predict State of Charge, State of Health, and Operational Risk")

st.divider()

# =========================================================
# INPUT FORM
# =========================================================
with st.form("battery_form"):
    col1, col2 = st.columns(2)

    terminal_voltage = col1.number_input("Terminal Voltage (V)", 300.0, 900.0, 620.0)
    battery_current  = col2.number_input("Battery Current (A)", 0.0, 500.0, 120.0)

    battery_temp  = col1.number_input("Battery Temperature (°C)", 0.0, 80.0, 35.0)
    ambient_temp  = col2.number_input("Ambient Temperature (°C)", 0.0, 60.0, 30.0)

    internal_resistance = col1.number_input(
        "Internal Resistance (Ω)", 0.0, 0.2, 0.045, format="%.4f"
    )

    thermal_stress_index = st.slider(
        "Thermal Stress Index", 0.0, 1.0, 0.40
    )

    charging_efficiency = st.slider(
        "Charging Efficiency", 0.0, 1.0, 0.92
    )

    submitted = st.form_submit_button("🔍 Predict Battery State")

# =========================================================
# PREDICTION LOGIC
# =========================================================
if submitted:
    input_data = {
        "terminal_voltage": terminal_voltage,
        "battery_current": battery_current,
        "battery_temp": battery_temp,
        "ambient_temp": ambient_temp,
        "internal_resistance": internal_resistance,
        "action_current": battery_current,
        "action_voltage": terminal_voltage,
        "dT_dt": 0.02,
        "dV_dt": -0.01,
        "soc_delta": -0.3,
        "thermal_stress_index": thermal_stress_index,
        "aging_indicator": 0.25,
        "charging_efficiency": charging_efficiency,
        "charging_time": 45,
        "cycle_degradation": 0.003,
        "over_temp_flag": int(battery_temp > 45),
        "over_voltage_flag": 0,
        "balancing_time": 5,
        "hour": 14,
        "dayofweek": 2,
    }

    X = pd.DataFrame([input_data])[MODEL_FEATURES]
    X_scaled = scaler.transform(X)

    soc_pred = soc_model.predict(X_scaled)[0]
    soh_pred = soh_model.predict(X_scaled)[0]

    if thermal_stress_index > 0.75 or battery_temp > 45:
        risk = "HIGH ⚠️"
        color = "red"
    elif thermal_stress_index > 0.5:
        risk = "MEDIUM"
        color = "orange"
    else:
        risk = "LOW ✅"
        color = "green"

    # =====================================================
    # OUTPUT
    # =====================================================
    st.divider()

    c1, c2, c3 = st.columns(3)

    c1.metric("Predicted SOC (%)", f"{soc_pred:.2f}")
    c2.metric("Predicted SOH (%)", f"{soh_pred:.2f}")
    c3.markdown(
        f"<h3 style='color:{color}; text-align:center'>{risk}</h3>",
        unsafe_allow_html=True
    )

    st.success("Prediction completed successfully.")
