import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
PORT = int(os.getenv("PORT", 5000))

# -----------------------------
# Paths
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

# -----------------------------
# Flask App
# -----------------------------
app = Flask(
    __name__,
    static_folder=STATIC_DIR,
    static_url_path="/static",
    template_folder=TEMPLATES_DIR
)

CORS(
    app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": "*"}}
)

# -----------------------------
# MongoDB Init
# -----------------------------
try:
    from db.mongo import db  # your mongo connection
    if db is not None:
        print(f"✅ MongoDB connected: Database '{getattr(db, 'name', 'Unknown')}'")
    else:
        print("⚠️ MongoDB is None, check your mongo.py configuration")
except Exception as e:
    print(f"❌ MongoDB import failed: {e}")
    sys.exit(1)

# -----------------------------
# Register Blueprints (No Auth)
# -----------------------------
try:
    from routes.dashboard import dashboard_bp
    from routes.logs import logs_bp
    from routes.maintenance import maintenance_bp
    from routes.prediction import prediction_bp
    from routes.route import route_bp

    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(logs_bp, url_prefix="/api/logs")
    app.register_blueprint(maintenance_bp, url_prefix="/api/maintenance")
    app.register_blueprint(prediction_bp, url_prefix="/api/prediction")
    app.register_blueprint(route_bp, url_prefix="/api/route")

    print("✅ All API blueprints registered successfully (no auth)")
except Exception as e:
    print(f"❌ Error registering blueprints: {e}")
    sys.exit(1)

# -----------------------------
# Frontend Page Routes
# -----------------------------
@app.route("/")
@app.route("/dashboard")
def index_page():
    return send_from_directory(TEMPLATES_DIR, "index.html")

@app.route("/logs")
def logs_page():
    return send_from_directory(TEMPLATES_DIR, "logs.html")

@app.route("/maintenance")
def maintenance_page():
    return send_from_directory(TEMPLATES_DIR, "maintenance.html")

@app.route("/prediction")
def prediction_page():
    return send_from_directory(TEMPLATES_DIR, "prediction.html")

@app.route("/route")
def route_page():
    return send_from_directory(TEMPLATES_DIR, "route.html")

# -----------------------------
# Serve Static Files
# -----------------------------
@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(STATIC_DIR, path)

# -----------------------------
# Health Check / Test API
# -----------------------------
@app.route("/api/health")
def health_check():
    return jsonify({"success": True, "message": "Backend is running", "mongo_connected": db is not None})

# -----------------------------
# Global Error Handlers
# -----------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    print(f"🚀 Backend starting at http://127.0.0.1:{PORT}")
    try:
        app.run(host="0.0.0.0", port=PORT, debug=True)
    except Exception as e:
        print(f"❌ Flask server failed to start: {e}")
        sys.exit(1)
