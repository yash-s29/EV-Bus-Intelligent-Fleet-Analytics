import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

# =====================================================
# PATHS
# =====================================================
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "ev_battery_charging.csv"
MODEL_DIR = BASE_DIR / "ml" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# LOAD DATA
# =====================================================
df = pd.read_csv(DATA_PATH)

df = df.drop_duplicates()
df = df.fillna(method="ffill").fillna(method="bfill")

df["timestamp"] = pd.to_datetime(df["timestamp"])
df["hour"] = df["timestamp"].dt.hour
df["dayofweek"] = df["timestamp"].dt.dayofweek

# =====================================================
# FEATURE CONTRACT (MUST MATCH app.py)
# =====================================================
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

X = df[MODEL_FEATURES]
y_soc = df["SOC"]
y_soh = df["SOH"]

# =====================================================
# TRAIN / TEST SPLIT
# =====================================================
X_train, X_test, y_soc_train, y_soc_test = train_test_split(
    X, y_soc, test_size=0.2, random_state=42
)

_, _, y_soh_train, y_soh_test = train_test_split(
    X, y_soh, test_size=0.2, random_state=42
)

# =====================================================
# SCALING (FOR SOH LINEAR MODEL)
# =====================================================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# =====================================================
# SOC MODEL — RANDOM FOREST REGRESSOR
# =====================================================
soc_model = RandomForestRegressor(
    n_estimators=300,
    max_depth=12,
    random_state=42,
    n_jobs=-1
)

soc_model.fit(X_train_scaled, y_soc_train)
soc_pred = soc_model.predict(X_test_scaled)

print("SOC MAE:", mean_absolute_error(y_soc_test, soc_pred))

# =====================================================
# SOH MODEL — LINEAR REGRESSION
# =====================================================
soh_model = LinearRegression()
soh_model.fit(X_train_scaled, y_soh_train)
soh_pred = soh_model.predict(X_test_scaled)

print("SOH MAE:", mean_absolute_error(y_soh_test, soh_pred))

# =====================================================
# SAVE MODELS
# =====================================================
joblib.dump(soc_model, MODEL_DIR / "soc_rf.pkl")
joblib.dump(soh_model, MODEL_DIR / "soh_lr.pkl")
joblib.dump(scaler, MODEL_DIR / "scaler.pkl")

print("✅ Models saved successfully")
