from functools import wraps
from typing import Callable, Iterable
from flask import request, jsonify
from utils.helpers import decode_jwt


def require_role(*allowed_roles: str) -> Callable:
    """
    Decorator to protect Flask routes using JWT + role-based access control.

    Example:
        @require_role("admin", "fleet_manager")
        def protected_route():
            ...

    Behavior:
    - Reads JWT from HTTP-only cookie `access_token`
    - Validates token
    - Checks user role
    - Injects `request.user` with decoded payload
    """

    if not allowed_roles:
        raise ValueError("require_role must be given at least one role")

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):

            # ---------------------------------
            # JWT COOKIE CHECK
            # ---------------------------------
            token = request.cookies.get("access_token")
            if not token:
                return jsonify(
                    success=False,
                    error="Unauthorized: missing access token"
                ), 401

            # ---------------------------------
            # DECODE & VALIDATE TOKEN
            # ---------------------------------
            payload = decode_jwt(token)
            if not payload or not isinstance(payload, dict):
                return jsonify(
                    success=False,
                    error="Unauthorized: invalid or expired token"
                ), 401

            # ---------------------------------
            # ROLE CHECK
            # ---------------------------------
            user_role = payload.get("role")
            if user_role not in allowed_roles:
                return jsonify(
                    success=False,
                    error="Forbidden: insufficient permissions",
                    required_roles=list(allowed_roles),
                    user_role=user_role
                ), 403

            # ---------------------------------
            # ATTACH USER CONTEXT
            # ---------------------------------
            request.user = {
                "user_id": payload.get("user_id"),
                "name": payload.get("name"),
                "email": payload.get("email"),
                "role": user_role
            }

            return fn(*args, **kwargs)

        return wrapper
    return decorator
