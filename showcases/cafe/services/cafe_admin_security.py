import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
import itsdangerous


def _get_secret_key() -> str:
    key = os.environ.get("CAFE_SECRET_KEY")
    if key:
        return key
    admin_pw = os.environ.get("CAFE_ADMIN_PASSWORD", "")
    if admin_pw:
        raise RuntimeError(
            "CAFE_SECRET_KEY must be set when CAFE_ADMIN_PASSWORD is configured"
        )
    return "dev-cafe-secret-change-me"


SECRET_KEY = _get_secret_key()
signer = itsdangerous.TimestampSigner(SECRET_KEY)


def is_admin_configured() -> bool:
    return bool(os.environ.get("CAFE_ADMIN_PASSWORD"))


def verify_admin(username: str, password: str) -> bool:
    if not is_admin_configured():
        return False
    if username != "admin":
        return False
    stored = os.environ.get("CAFE_ADMIN_PASSWORD", "")
    if stored.startswith("pbkdf2:"):
        return check_password_hash(stored, password)
    h = generate_password_hash(stored, method="pbkdf2:sha256")
    return check_password_hash(h, password)


def generate_csrf_token() -> str:
    raw = secrets.token_urlsafe(32)
    return signer.sign(raw.encode()).decode()


def validate_csrf_token(token: str) -> bool:
    try:
        signer.unsign(token, max_age=3600)
        return True
    except Exception:
        return False
