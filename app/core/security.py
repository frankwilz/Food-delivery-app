"""Password hashing with salted PBKDF2-SHA256 from the standard library.

A stored hash looks like `pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>`, so the
salt and the work factor travel with the hash and can be raised later.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP's recommended minimum for PBKDF2-SHA256
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)  # a fresh random salt per password
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$")
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    # compare_digest takes the same time whether or not the hashes match
    return hmac.compare_digest(digest.hex(), digest_hex)
