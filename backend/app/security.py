"""Password hashing and signed access tokens."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.config import get_settings


def hash_password(password: str) -> str:
    settings = get_settings()
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int) -> tuple[str, str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    token_id = str(uuid.uuid4())
    payload = {"sub": str(user_id), "jti": token_id, "exp": expires_at}
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, token_id, expires_at


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc
