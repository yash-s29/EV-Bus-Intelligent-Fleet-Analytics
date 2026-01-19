# security.py
from passlib.hash import bcrypt
from typing import Optional

MAX_BCRYPT_LENGTH = 72  # bcrypt limitation

def hash_password(password: str, rounds: Optional[int] = 12) -> str:
    """
    Hash a plaintext password using bcrypt (safe for Windows & passlib==1.7.4).

    Automatically truncates passwords longer than 72 bytes.

    Args:
        password (str): Plaintext password
        rounds (int, optional): bcrypt work factor (default=12)

    Returns:
        str: Hashed password

    Raises:
        ValueError: If password is empty
    """
    if not password:
        raise ValueError("Password cannot be empty")

    # Truncate if too long
    truncated = password[:MAX_BCRYPT_LENGTH]

    try:
        return bcrypt.using(rounds=rounds).hash(truncated)
    except Exception as e:
        raise ValueError(f"❌ Password hashing failed: {e}")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Truncates password >72 bytes automatically for verification.

    Args:
        password (str): Plaintext password
        hashed (str): Stored bcrypt hash

    Returns:
        bool: True if password matches hash, False otherwise
    """
    if not password or not hashed:
        return False

    try:
        truncated = password[:MAX_BCRYPT_LENGTH]
        return bcrypt.verify(truncated, hashed)
    except ValueError:
        # Handles corrupt or invalid bcrypt hashes
        return False
    except Exception:
        # Catch any unexpected errors
        return False
