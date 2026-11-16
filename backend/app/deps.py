"""Authentication and project ownership dependencies."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Expense, Project, RevokedToken, User
from app.security import decode_access_token
from app.services.audit import client_ip, write_audit

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from None
    user_id = payload.get("sub")
    token_id = payload.get("jti")
    if not user_id or not token_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    revoked = db.query(RevokedToken).filter(RevokedToken.jti == token_id).first()
    if revoked is not None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def get_owned_project(project_id: int, db: Session, user: User, request: Request | None = None) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        write_audit(
            "access_denied",
            user_id=user.id,
            ip_address=client_ip(request),
            detail=f"project_id={project_id}",
        )
        raise HTTPException(status_code=403, detail="You do not have access to this project")
    return project


def get_owned_expense(expense_id: int, db: Session, user: User, request: Request | None = None) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    project = db.get(Project, expense.project_id)
    if project is None or project.owner_id != user.id:
        write_audit(
            "access_denied",
            user_id=user.id,
            ip_address=client_ip(request),
            detail=f"expense_id={expense_id}",
        )
        raise HTTPException(status_code=403, detail="You do not have access to this expense")
    return expense


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
