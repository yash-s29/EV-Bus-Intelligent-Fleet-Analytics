import time
from pymongo import MongoClient, errors
from config import Config

# =========================================================
# Global DB handles (used by routes)
# =========================================================
client = None
db = None

users = None
telemetry_logs = None
trip_predictions = None
maintenance_health = None

# =========================================================
# Configuration
# =========================================================
ATLAS_URI = Config.MONGO_ATLAS_URI
LOCAL_URI = Config.MONGO_LOCAL_URI
DB_NAME = Config.DB_NAME

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
TIMEOUT_MS = 5000


# =========================================================
# Internal connection helper
# =========================================================
def _try_connect(uri: str, label: str):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"🔌 Connecting to {label} (attempt {attempt}/{MAX_RETRIES})")

            c = MongoClient(
                uri,
                serverSelectionTimeoutMS=TIMEOUT_MS,
                retryWrites=True,
                w="majority",
                tls=True if uri.startswith("mongodb+srv") else False
            )

            # Force handshake
            c.admin.command("ping")

            print(f"✅ Connected to {label}")
            return c

        except errors.ServerSelectionTimeoutError as e:
            print(f"⚠️ {label} timeout: {e}")
            time.sleep(RETRY_DELAY)

        except errors.ConnectionFailure as e:
            print(f"⚠️ {label} connection failure: {e}")
            time.sleep(RETRY_DELAY)

        except Exception as e:
            print(f"❌ {label} unexpected error: {e}")
            break

    print(f"❌ {label} unreachable")
    return None


# =========================================================
# Public initializer
# =========================================================
def init_mongo():
    global client, db
    global users, telemetry_logs, trip_predictions, maintenance_health

    if not ATLAS_URI and not LOCAL_URI:
        raise RuntimeError("❌ No MongoDB URIs configured")

    # 1️⃣ Try Atlas first
    if ATLAS_URI:
        client = _try_connect(ATLAS_URI, "MongoDB Atlas")

    # 2️⃣ Fallback to local
    if client is None and LOCAL_URI:
        client = _try_connect(LOCAL_URI, "Local MongoDB")

    # 3️⃣ Absolute failure
    if client is None:
        print("🚨 MongoDB unavailable — backend running in DEGRADED MODE")
        return None, None

    # 4️⃣ Bind database & collections
    db = client[DB_NAME]

    users = db["users"]
    telemetry_logs = db["telemetry_logs"]
    trip_predictions = db["trip_predictions"]
    maintenance_health = db["maintenance_health"]

    source = "atlas" if client.address and "mongodb.net" in str(client.address) else "local"
    print(f"📊 Database source: {source}")

    return client, db


# =========================================================
# Initialize on startup (safe)
# =========================================================
init_mongo()
