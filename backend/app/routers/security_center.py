"""Security Center catalog, deployment checklist, and audit history."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.constants import CHECKLIST_ITEMS, THREATS
from app.deps import CurrentUser, DbSession
from app.models import ChecklistState, SecurityAuditLog
from app.schemas import AuditPage, ChecklistItemOut, ChecklistUpdate, ThreatOut

router = APIRouter(prefix="/api/security", tags=["Security"])


@router.get("/threats", response_model=list[ThreatOut])
def threats(current: CurrentUser):
    return [ThreatOut(**item) for item in THREATS]


@router.get("/checklist", response_model=list[ChecklistItemOut])
def checklist(current: CurrentUser, db: DbSession):
    existing = {
        row.item_key: row
        for row in db.query(ChecklistState).filter(ChecklistState.user_id == current.id).all()
    }
    results = []
    for item in CHECKLIST_ITEMS:
        row = existing.get(item["key"])
        if row is None:
            row = ChecklistState(user_id=current.id, item_key=item["key"], completed=False)
            db.add(row)
            db.flush()
        results.append(
            ChecklistItemOut(
                key=item["key"],
                title=item["title"],
                guidance=item["guidance"],
                completed=bool(row.completed),
                updated_at=row.updated_at,
            )
        )
    db.commit()
    return results


@router.put("/checklist/{item_key}", response_model=ChecklistItemOut)
def update_checklist(item_key: str, payload: ChecklistUpdate, current: CurrentUser, db: DbSession):
    definition = next((item for item in CHECKLIST_ITEMS if item["key"] == item_key), None)
    if definition is None:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    row = (
        db.query(ChecklistState)
        .filter(ChecklistState.user_id == current.id, ChecklistState.item_key == item_key)
        .first()
    )
    if row is None:
        row = ChecklistState(user_id=current.id, item_key=item_key, completed=payload.completed)
        db.add(row)
    else:
        row.completed = payload.completed
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return ChecklistItemOut(
        key=definition["key"],
        title=definition["title"],
        guidance=definition["guidance"],
        completed=bool(row.completed),
        updated_at=row.updated_at,
    )


@router.get("/audit", response_model=AuditPage)
def audit(current: CurrentUser, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    query = db.query(SecurityAuditLog).filter(SecurityAuditLog.user_id == current.id)
    total = query.count()
    rows = query.order_by(SecurityAuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return AuditPage(
        items=[
            {"id": row.id, "event_type": row.event_type, "detail": row.detail, "created_at": row.created_at}
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
