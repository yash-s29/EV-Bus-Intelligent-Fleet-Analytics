import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from functools import wraps
from flask import request, jsonify
from bson.objectid import ObjectId

from config import Config
from db.mongo import users

# -----------------------------
# JWT GENERATION
# -----------------------------
def generate_jwt(user: Dict[str, Any], expires_hours: Optional[int] = None) -> str:
    """
    Generate a JWT token for a user.

    Args:
        user (dict): User dictionary containing '_id', 'role', 'name', 'email'
        expires_hours (int, optional): Token expiration in hours. Defaults to Config.JWT_EXP_HOURS.

    Returns:
        str: Encoded JWT token
    """
    if expires_hours is None:
        expires_hours = getattr(Config, "JWT_EXP_HOURS", 12)

    payload = {
        "user_id": str(user.get("_id") or user.get("user_id")),
        "name": user.get("name", ""),
        "email": user.get("email", ""),
        "role": user.get("role", "technician"),
        "exp": datetime.utcnow() + timedelta(hours=expires_hours)
    }

    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    # PyJWT >=2 returns str, older versions may return bytes
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


# -----------------------------
# JWT DECODING
# -----------------------------
def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode a JWT token and return its payload.

    Args:
        token (str): JWT token string

    Returns:
        dict or None: Payload if valid, None if expired or invalid
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


# -----------------------------
# ROLE CHECK
# -----------------------------
def is_admin(token: str) -> bool:
    """
    Check if the token belongs to an admin user.

    Args:
        token (str): JWT token

    Returns:
        bool: True if admin, False otherwise
    """
    payload = decode_jwt(token)
    return bool(payload and payload.get("role") == "admin")


# -----------------------------
# FLASK DECORATOR
# -----------------------------
def token_required(roles: Optional[List[str]] = None) -> Callable:
    """
    Flask route decorator to enforce JWT authentication and optional role checks.

    Args:
        roles (list[str], optional): List of allowed roles. If None, all authenticated users are allowed.

    Returns:
        Callable: Decorator for Flask route
    """
    roles = roles or []

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"success": False, "error": "Authorization header missing"}), 401

            token = auth_header.split(" ")[1]
            payload = decode_jwt(token)
            if not payload:
                return jsonify({"success": False, "error": "Invalid or expired token"}), 401

            # Role enforcement
            if roles and payload.get("role") not in roles:
                return jsonify({"success": False, "error": "Forbidden"}), 403

            # Attach user object to route
            user_id = payload.get("user_id")
            current_user = users.find_one({"_id": ObjectId(user_id)})
            if not current_user:
                return jsonify({"success": False, "error": "User not found"}), 401

            return f(current_user, *args, **kwargs)

        return wrapper

    return decorator
