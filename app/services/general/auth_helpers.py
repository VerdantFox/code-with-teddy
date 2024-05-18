"""auth_helpers: Authorization helpers."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plain password against a hashed version of the password."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
