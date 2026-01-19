import os
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import StandardScaler


class FeatureBuilder:
    """
    Canonical feature engineering pipeline for EV Fleet ML.
    SAME logic must be used for training and inference.
    """

    def __init__(self, scaler_path=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.models_dir = os.path.join(base_dir, "models")

        self.scaler_path = scaler_path or os.path.join(self.models_dir, "scaler.pkl")

        self.trip_features = [
            "start_soc",
            "route_distance_km",
            "avg_speed_kmph",
            "passenger_load"
        ]

        self.soh_features = [
            "battery_cycles",
            "avg_depth_of_discharge",
            "temperature_variance"
        ]

        self.scaler = None
        if os.path.exists(self.scaler_path):
            self.scaler = joblib.load(self.scaler_path)

    # --------------------------------------------------
    # Training preprocessing
    # --------------------------------------------------
    def build_trip_training_features(self, df: pd.DataFrame):
        """
        Builds training matrix for trip feasibility model
        """
        required = self.trip_features + ["energy_consumed_pct"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing training columns: {missing}")

        X = df[self.trip_features].astype(float).values
        y = df["energy_consumed_pct"].astype(float).values

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        joblib.dump(self.scaler, self.scaler_path)

        return X_scaled, y

    def build_soh_training_features(self, df: pd.DataFrame):
        """
        Builds training matrix for battery SOH model
        """
        required = self.soh_features + ["soh"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing training columns: {missing}")

        X = df[self.soh_features].astype(float).values
        y = df["soh"].astype(float).values

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        joblib.dump(self.scaler, self.scaler_path)

        return X_scaled, y

    # --------------------------------------------------
    # Inference preprocessing
    # --------------------------------------------------
    def build_trip_inference_features(self, input_dict: dict):
        """
        Converts API input → model-ready numpy array
        """
        missing = [f for f in self.trip_features if f not in input_dict]
        if missing:
            raise ValueError(f"Missing inference features: {missing}")

        X = np.array(
            [[float(input_dict[f]) for f in self.trip_features]]
        )

        if self.scaler:
            X = self.scaler.transform(X)

        return X

    def build_soh_inference_features(self, input_dict: dict):
        """
        Converts API input → model-ready numpy array
        """
        missing = [f for f in self.soh_features if f not in input_dict]
        if missing:
            raise ValueError(f"Missing inference features: {missing}")

        X = np.array(
            [[float(input_dict[f]) for f in self.soh_features]]
        )

        if self.scaler:
            X = self.scaler.transform(X)

        return X
