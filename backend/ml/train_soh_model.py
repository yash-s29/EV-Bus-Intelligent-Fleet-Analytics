import os
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


def build_soh_dataset(df: pd.DataFrame):
    """
    Builds cycle-aware degradation dataset
    """

    required_cols = [
        "battery_id",
        "cycle_count",
        "internal_resistance",
        "thermal_stress_index",
        "SOH"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Sort by lifecycle
    df = df.sort_values(["battery_id", "cycle_count"])

    # Rolling degradation features
    df["resistance_growth"] = (
        df.groupby("battery_id")["internal_resistance"]
        .diff()
        .fillna(0)
    )

    df["thermal_avg_50"] = (
        df.groupby("battery_id")["thermal_stress_index"]
        .rolling(50)
        .mean()
        .reset_index(level=0, drop=True)
        .fillna(df["thermal_stress_index"])
    )

    features = [
        "cycle_count",
        "internal_resistance",
        "resistance_growth",
        "thermal_avg_50"
    ]

    X = df[features]
    y = df["SOH"]

    return X, y


def train_soh_model():
    print("🔋 Training SOH Forecast Model")

    # ----------------------------
    # Load raw telemetry
    # ----------------------------
    df = pd.read_csv("data/raw/ev_battery_charging.csv")

    # ----------------------------
    # Build degradation dataset
    # ----------------------------
    X, y = build_soh_dataset(df)

    # ----------------------------
    # Scale features
    # ----------------------------
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ----------------------------
    # Train / Test split
    # ----------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    # ----------------------------
    # Train model
    # ----------------------------
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    print(f"📊 SOH Model R² Score: {round(score, 3)}")

    # ----------------------------
    # Save model + scaler
    # ----------------------------
    models_dir = os.path.join("ml", "models")
    os.makedirs(models_dir, exist_ok=True)

    joblib.dump(model, os.path.join(models_dir, "soh_forecast.pkl"))
    joblib.dump(scaler, os.path.join(models_dir, "soh_scaler.pkl"))

    print("✅ SOH model and scaler saved")


if __name__ == "__main__":
    train_soh_model()
