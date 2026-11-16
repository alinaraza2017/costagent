"""Registration, login, logout, and profile routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import CurrentUser, DbSession
from app.limiter import limiter
from app.models import RevokedToken, User
from app.schemas import (
    LoginRequest,
    MessageOut,
    PasswordChangeRequest,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.audit import client_ip, write_audit

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _public_user(user: User) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
        ai_mode=get_settings().ai_mode,
    )


@router.post("/register", response_model=UserPublic, status_code=201)
@limiter.limit(lambda: get_settings().register_rate_limit)
def register(request: Request, payload: RegisterRequest, db: DbSession):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit("register_success", user_id=user.id, ip_address=client_ip(request), detail="account created")
    return _public_user(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(lambda: get_settings().login_rate_limit)
def login(request: Request, payload: LoginRequest, db: DbSession):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        write_audit("login_failure", user_id=None, ip_address=client_ip(request), detail="rejected credentials")
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token, _token_id, _expires = create_access_token(user.id)
    write_audit("login_success", user_id=user.id, ip_address=client_ip(request), detail="session started")
    return TokenResponse(access_token=token, expires_in=get_settings().access_token_expire_minutes * 60)


@router.post("/logout", response_model=MessageOut)
def logout(request: Request, current: CurrentUser, db: DbSession):
    header = request.headers.get("authorization", "")
    token = header.split(" ", 1)[1].strip() if header.lower().startswith("bearer ") else ""
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    token_id = payload.get("jti")
    exp = payload.get("exp")
    if token_id:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if isinstance(exp, (int, float)) else datetime.now(timezone.utc)
        already = db.query(RevokedToken).filter(RevokedToken.jti == token_id).first()
        if already is None:
            db.add(RevokedToken(jti=token_id, expires_at=expires_at))
        db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
        db.commit()
    write_audit("logout", user_id=current.id, ip_address=client_ip(request), detail="session ended")
    return MessageOut(message="Signed out")


@router.get("/me", response_model=UserPublic)
def me(current: CurrentUser):
    return _public_user(current)


@router.put("/me", response_model=UserPublic)
def update_me(payload: ProfileUpdate, current: CurrentUser, db: DbSession):
    current.full_name = payload.full_name
    db.add(current)
    db.commit()
    db.refresh(current)
    write_audit("profile_updated", user_id=current.id, detail="profile name updated")
    return _public_user(current)


@router.post("/change-password", response_model=MessageOut)
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
def change_password(request: Request, payload: PasswordChangeRequest, current: CurrentUser, db: DbSession):
    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current.password_hash = hash_password(payload.new_password)
    db.add(current)
    db.commit()
    write_audit("credentials_updated", user_id=current.id, ip_address=client_ip(request), detail="credentials updated")
    return MessageOut(message="Password updated")
