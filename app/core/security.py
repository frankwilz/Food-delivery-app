"""Password hashing and login tokens.

Passwords use salted PBKDF2-SHA256 from the standard library. A stored hash looks like
`pbkdf2_sha256$<iterations>$<salt hex>$<hash hex>`, so the salt and the work factor travel
with the hash and can be raised later.

Login tokens are JWTs signed with HS256 (PyJWT). A token only carries the customer id and an
expiry time; the customer record itself is always read from the repository.
"""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP's recommended minimum for PBKDF2-SHA256
SALT_BYTES = 16
TOKEN_ALGORITHM = "HS256"


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


def create_access_token(customer_id: int, expires_in: timedelta | None = None) -> str:
    if expires_in is None:
        expires_in = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {"sub": str(customer_id), "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, SECRET_KEY, algorithm=TOKEN_ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Return the customer id inside a token, or None if it is malformed, tampered with or expired."""
    try:
        # Naming the algorithm stops a token from choosing its own (e.g. "none")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[TOKEN_ALGORITHM], options={"require": ["sub", "exp"]})
        return int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None
