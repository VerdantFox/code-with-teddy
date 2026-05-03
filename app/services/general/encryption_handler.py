"""encryption_helpers: functions for encrypting and decrypting data."""

import hashlib
import hmac

from app.settings import settings


def hash_token(token: str) -> str:
    """Return an HMAC-SHA256 hex digest of `token` keyed with the encryption key.

    Using HMAC rather than a bare SHA-256 hash prevents offline rainbow-table
    attacks: an attacker who obtains the DB rows cannot pre-compute hashes
    without also knowing the secret key.

    The token is a UUID (128 bits of entropy), so HMAC-SHA256 is sufficient —
    a slow KDF such as bcrypt is not required.

    Args:
    ----
        token: The plaintext token (UUID string) to hash.

    Returns:
    -------
        A 64-character lowercase hex string (256-bit HMAC digest).

    """
    key_bytes = bytes.fromhex(settings.encryption_key)
    return hmac.new(key_bytes, token.encode("utf-8"), hashlib.sha256).hexdigest()


if __name__ == "__main__":  # pragma: no cover
    import uuid

    data = str(uuid.uuid4())
    print("Token:", data)  # noqa: T201 (print used for example)
    print("Hashed:", hash_token(data))  # noqa: T201 (print used for example)
