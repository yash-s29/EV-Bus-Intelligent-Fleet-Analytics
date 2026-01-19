import os
from dotenv import load_dotenv
from pathlib import Path

# =========================================================
# Load environment variables
# =========================================================
load_dotenv()


class Config:
    """
    Central configuration for EV Fleet AI Backend.
    Supports MongoDB Atlas with automatic local fallback.
    """

    # =====================================================
    # Environment
    # =====================================================
    ENV: str = os.getenv("ENV", "development").lower()

    # =====================================================
    # Base paths
    # =====================================================
    BASE_DIR: Path = Path(__file__).resolve().parent
    FRONTEND_DIR: Path = BASE_DIR.parent / "frontend"
    TEMPLATES_DIR: Path = FRONTEND_DIR / "templates"
    STATIC_DIR: Path = FRONTEND_DIR / "static"
    ML_MODELS_DIR: Path = BASE_DIR.parent / "ml" / "models"

    # =====================================================
    # MongoDB Configuration (CRITICAL FIX)
    # =====================================================
    # Cloud (Primary)
    MONGO_ATLAS_URI: str | None = os.getenv("MONGO_ATLAS_URI")

    # Local (Fallback)
    MONGO_LOCAL_URI: str = os.getenv(
        "MONGO_LOCAL_URI",
        "mongodb://127.0.0.1:27017/ev_fleet_ai"
    )

    DB_NAME: str = os.getenv("DB_NAME", "ev_fleet_ai")

    # Connection tuning
    MONGO_CONNECT_TIMEOUT: int = int(os.getenv("MONGO_CONNECT_TIMEOUT", "5000"))
    MONGO_RETRIES: int = int(os.getenv("MONGO_RETRIES", "3"))

    # =====================================================
    # JWT / Authentication
    # =====================================================
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-key")
    JWT_EXP_HOURS: int = int(os.getenv("JWT_EXP_HOURS", "24"))

    # =====================================================
    # Flask / Backend server settings
    # =====================================================
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    # =====================================================
    # ML Models
    # =====================================================
    SOC_MODEL_PATH: Path = ML_MODELS_DIR / "trip_feasibility.pkl"
    SOH_MODEL_PATH: Path = ML_MODELS_DIR / "soh_forecast.pkl"
    SCALER_PATH: Path = ML_MODELS_DIR / "scaler.pkl"

    # =====================================================
    # Validation
    # =====================================================
    @classmethod
    def validate(cls) -> None:
        errors = []

        if not cls.DB_NAME:
            errors.append("DB_NAME")

        # In production, Atlas is mandatory
        if cls.ENV == "production" and not cls.MONGO_ATLAS_URI:
            errors.append("MONGO_ATLAS_URI (required in production)")

        if errors:
            raise RuntimeError(f"Missing critical config: {', '.join(errors)}")

        if cls.ENV != "production" and not cls.MONGO_ATLAS_URI:
            print("⚠️ MongoDB Atlas not configured — local MongoDB fallback enabled")

        if cls.JWT_SECRET == "dev-secret-key":
            print("⚠️ Using default JWT_SECRET (development only)")

    # =====================================================
    # Debug summary
    # =====================================================
    @classmethod
    def print_summary(cls) -> None:
        print("\n📌 Backend Config Summary")
        print("--------------------------------------------------")
        print(f"ENV: {cls.ENV}")
        print(f"Mongo Atlas: {'SET' if cls.MONGO_ATLAS_URI else 'NOT SET'}")
        print(f"Mongo Local: {cls.MONGO_LOCAL_URI}")
        print(f"DB Name: {cls.DB_NAME}")
        print(f"Timeout: {cls.MONGO_CONNECT_TIMEOUT} ms")
        print(f"Retries: {cls.MONGO_RETRIES}")
        print(f"Port: {cls.PORT}, Debug: {cls.DEBUG}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("--------------------------------------------------")

        cls.validate()
        print("✅ Config validation passed\n")


# =========================================================
# Auto-validate on import
# =========================================================
try:
    Config.validate()
except RuntimeError as e:
    raise SystemExit(f"❌ Config validation failed: {e}")


# =========================================================
# Test mode
# =========================================================
if __name__ == "__main__":
    Config.print_summary()
