"""Security audit records that exclude secrets and financial amounts."""

from datetime import datetime, timezone

from fastapi import Request

from app.database import SessionLocal
from app.logging_config import logger
from app.models import SecurityAuditLog

BANNED_DETAIL_WORDS = ("password", "token", "secret", "api_key", "bearer", "authorization")


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def write_audit(event_type: str, user_id: int | None = None, ip_address: str | None = None, detail: str = "") -> None:
    safe_detail = (detail or "")[:300]
    lowered = safe_detail.lower()
    if any(word in lowered for word in BANNED_DETAIL_WORDS):
        safe_detail = "detail redacted"
    db = SessionLocal()
    try:
        db.add(
            SecurityAuditLog(
                user_id=user_id,
                event_type=event_type[:64],
                ip_address=ip_address,
                detail=safe_detail,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.error("audit_write_failed event_type=%s", event_type)
    finally:
        db.close()
