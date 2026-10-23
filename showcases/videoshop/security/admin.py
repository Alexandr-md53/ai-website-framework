"""Showcase-local admin authentication: PBKDF2 passwords + signed cookie sessions.

Rules (step 5 of the product slice):

* **no secrets and no default password in the code**: the credential comes from
  the environment (``VIDEOSHOP_ADMIN_PASSWORD_HASH`` preferred, or
  ``VIDEOSHOP_ADMIN_PASSWORD`` which is hashed in memory at startup) together
  with ``VIDEOSHOP_SECRET_KEY``. When either is missing the admin area is
  **disabled** and every admin operation is refused - there is no fallback
  password and no "development default";
* passwords are stored/verified with stdlib PBKDF2-HMAC-SHA256 (``passlib`` and
  ``bcrypt`` are not installed and no new dependency is added);
* the session is a stateless cookie ``base64url(payload).base64url(HMAC-SHA256)``
  with an expiry; verification uses ``hmac.compare_digest``;
* every mutating request must also carry a CSRF token derived from the session
  cookie, so a valid session alone is not enough to issue a POST.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Mapping, Optional

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16
DEFAULT_SESSION_TTL_SECONDS = 8 * 3600

#: cookie carrying the signed admin session
COOKIE_NAME = "videoshop_admin"

ENV_USERNAME = "VIDEOSHOP_ADMIN_USER"
ENV_PASSWORD = "VIDEOSHOP_ADMIN_PASSWORD"
ENV_PASSWORD_HASH = "VIDEOSHOP_ADMIN_PASSWORD_HASH"
ENV_SECRET = "VIDEOSHOP_SECRET_KEY"
ENV_TTL = "VIDEOSHOP_SESSION_TTL_SECONDS"


class AdminConfigError(RuntimeError):
    """The admin area is not configured (fail closed)."""

    code = "ADMIN_CONFIG_ERROR"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode((text + "=" * (-len(text) % 4)).encode("ascii"))


def hash_password(
    password: str,
    *,
    iterations: int = PBKDF2_ITERATIONS,
    salt: Optional[bytes] = None,
) -> str:
    """Return ``pbkdf2_sha256$iterations$salt$hash`` for a password."""
    if not password or not password.strip():
        raise ValueError("password must not be empty")
    salt = salt or secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return f"{PBKDF2_ALGORITHM}${int(iterations)}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification of an encoded PBKDF2 password."""
    try:
        algorithm, iterations, salt_b64, digest_b64 = (encoded or "").split("$")
        if algorithm != PBKDF2_ALGORITHM:
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(digest_b64)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", (password or "").encode("utf-8"), salt, int(iterations)
        )
    except Exception:
        return False
    return hmac.compare_digest(candidate, expected)


@dataclass(frozen=True)
class AdminConfig:
    """Configured admin credential + session signing key."""

    username: str
    password_hash: str
    secret_key: bytes
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> Optional["AdminConfig"]:
        """Build the configuration from the environment, or ``None`` (disabled)."""
        source = os.environ if env is None else env
        secret = (source.get(ENV_SECRET) or "").strip()
        password_hash = (source.get(ENV_PASSWORD_HASH) or "").strip()
        password = (source.get(ENV_PASSWORD) or "").strip()
        if not secret or not (password_hash or password):
            return None
        username = (source.get(ENV_USERNAME) or "admin").strip() or "admin"
        if not password_hash:
            password_hash = hash_password(password)
        ttl_raw = (source.get(ENV_TTL) or "").strip()
        try:
            ttl = int(ttl_raw) if ttl_raw else DEFAULT_SESSION_TTL_SECONDS
        except ValueError:
            ttl = DEFAULT_SESSION_TTL_SECONDS
        return cls(
            username=username,
            password_hash=password_hash,
            secret_key=secret.encode("utf-8"),
            session_ttl_seconds=max(60, ttl),
        )

    # --- authentication -------------------------------------------------

    def check_credentials(self, username: str, password: str) -> bool:
        user_ok = hmac.compare_digest((username or "").strip(), self.username)
        password_ok = verify_password(password or "", self.password_hash)
        return user_ok and password_ok

    # --- sessions -------------------------------------------------------

    def _sign(self, body: str) -> str:
        return _b64e(hmac.new(self.secret_key, body.encode("ascii"), hashlib.sha256).digest())

    def issue_session(self, *, now: Optional[float] = None, nonce: Optional[str] = None) -> str:
        issued = time.time() if now is None else now
        payload = {
            "u": self.username,
            "exp": int(issued + self.session_ttl_seconds),
            "n": nonce or secrets.token_hex(8),
        }
        body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        return f"{body}.{self._sign(body)}"

    def session_payload(self, token: Optional[str], *, now: Optional[float] = None) -> Optional[dict]:
        if not token or "." not in token:
            return None
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(self._sign(body), signature):
            return None
        try:
            payload = json.loads(_b64d(body).decode("utf-8"))
        except Exception:
            return None
        current = time.time() if now is None else now
        if payload.get("u") != self.username:
            return None
        if int(payload.get("exp", 0)) < int(current):
            return None
        return payload

    def read_session(self, token: Optional[str], *, now: Optional[float] = None) -> Optional[str]:
        payload = self.session_payload(token, now=now)
        return None if payload is None else str(payload.get("u"))

    # --- CSRF -----------------------------------------------------------

    def csrf_token(self, token: Optional[str]) -> str:
        base = (token or "").encode("utf-8")
        return _b64e(hmac.new(self.secret_key, b"csrf:" + base, hashlib.sha256).digest())

    def check_csrf(self, token: Optional[str], candidate: Optional[str]) -> bool:
        if not token or not candidate:
            return False
        return hmac.compare_digest(self.csrf_token(token), candidate)
