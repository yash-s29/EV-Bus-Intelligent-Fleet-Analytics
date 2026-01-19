import os
import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

from feature_builder import FeatureBuilder


def build_trip_dataset(df: pd.DataFrame):
    """
    Converts raw telemetry → trip-level training samples
    """

    # Simulated trip-level aggregation
    trip_df = pd.DataFrame({
        "start_soc": df.groupby("trip_id")["SOC"].first(),
        "end_soc": df.groupby("trip_id")["SOC"].last(),
        "route_distance_km": df.groupby("trip_id")["distance_km"].max(),
        "avg_speed_kmph": df.groupby("trip_id")["speed_kmph"].mean(),
        "passenger_load": df.groupby("trip_id")["passenger_count"].mean(),
    }).reset_index(drop=True)

    trip_df["energy_consumed_pct"] = (
        trip_df["start_soc"] - trip_df["end_soc"]
    )

    return trip_df


def train_trip_model():
    print("🚀 Training Trip Feasibility Model")

    # ----------------------------
    # Load raw telemetry
    # ----------------------------
    df = pd.read_csv("data/raw/ev_battery_charging.csv")

    required_cols = [
        "trip_id",
        "SOC",
        "distance_km",
        "speed_kmph",
        "passenger_count"
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ----------------------------
    # Build trip-level dataset
    # ----------------------------
    trip_df = build_trip_dataset(df)

    # ----------------------------
    # Feature engineering
    # ----------------------------
    fb = FeatureBuilder()
    X, y = fb.build_trip_training_features(trip_df)

    # ----------------------------
    # Train / Test split
    # ----------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ----------------------------
    # Train model
    # ----------------------------
    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    print(f"📊 Model R² Score: {round(score, 3)}")

    # ----------------------------
    # Save model
    # ----------------------------
    models_dir = os.path.join("ml", "models")
    os.makedirs(models_dir, exist_ok=True)

    model_path = os.path.join(models_dir, "trip_feasibility.pkl")
    joblib.dump(model, model_path)

    print(f"✅ Trip Feasibility Model saved → {model_path}")


if __name__ == "__main__":
    train_trip_model()
