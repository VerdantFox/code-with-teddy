"""encryption_helpers: functions for encrypting and decrypting data."""

import base64
import hashlib

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.settings import settings

ENCRYPTION_KEY = settings.encryption_key


def derive_iv(plaintext: str) -> bytes:
    """Derive a consistent IV from the plaintext using a hash function.

    Args:
    ----
        plaintext (str): The plaintext from which to derive the IV.

    Returns:
    -------
        bytes: A 16-byte IV derived from the plaintext.

    """
    return hashlib.sha256(plaintext.encode("utf-8")).digest()[:16]


def encrypt(data: str) -> str:
    """Encrypt the given data using AES encryption and encodes it in Base64.

    Args:
    ----
        data (str): The data to be encrypted.

    Returns:
    -------
        str: The Base64 encoded encrypted data including the IV.

    """
    key_bytes = bytes.fromhex(ENCRYPTION_KEY)
    data_bytes = data.encode("utf-8")
    iv = derive_iv(data)
    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    # Pad data to be a multiple of block size
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data_bytes) + padder.finalize()

    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    encrypted_data_with_iv = iv + encrypted_data

    # Encode the encrypted data with IV in Base64
    return base64.b64encode(encrypted_data_with_iv).decode("utf-8")


def decrypt(encoded_data: str) -> str:
    """Decrypt the given Base64 encoded encrypted data using AES decryption.

    Args:
    ----
        encoded_data (str): The Base64 encoded encrypted data including the IV.

    Returns:
    -------
        str: The decrypted data as a string.

    """
    key_bytes = bytes.fromhex(ENCRYPTION_KEY)
    encrypted_data_with_iv = base64.b64decode(encoded_data)

    iv = encrypted_data_with_iv[:16]
    encrypted_data = encrypted_data_with_iv[16:]

    cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    # Unpad data
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    data_bytes = unpadder.update(padded_data) + unpadder.finalize()

    return data_bytes.decode("utf-8")


if __name__ == "__main__":  # pragma: no cover
    # Encryption key as a 64-character hex string (256 bits / 32 bytes)
    # key = os.urandom(32).hex()  # noqa: ERA001 (commented-out code)
    print(f"Key (hex): {ENCRYPTION_KEY}")  # noqa: T201 (print used for example)

    import uuid

    # Original plaintext data
    data = str(uuid.uuid4())
    print("Original Data:", data)  # noqa: T201 (print used for example)

    # Encrypt the data to get the encrypted value
    encrypted_data = encrypt(data)
    print("Encrypted Data:", encrypted_data)  # noqa: T201 (print used for example)

    # Decrypt the data to get the original value back
    decrypted_data = decrypt(encrypted_data)
    print("Decrypted Data:", decrypted_data)  # noqa: T201 (print used for example)

    # To search for the encrypted data if you know the decrypted data
    known_decrypted_data = data
    encrypted_search_value = encrypt(known_decrypted_data)
    print("Encrypted Search Value:", encrypted_search_value)  # noqa: T201 (print used for example)

    # Check if the encrypted data matches the search value
    print("Match found:", encrypted_data == encrypted_search_value)  # noqa: T201 (print used for example)
