"""Spreadsheet preview and confirmation routes."""

import json

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from app.constants import DUPLICATE_POLICY, SAMPLE_TEMPLATE_NOTE
from app.deps import CurrentUser, DbSession, get_owned_project
from app.limiter import limiter
from app.models import ImportSession
from app.config import get_settings
from app.schemas import ImportConfirmIn, ImportPreviewOut, ImportSummaryOut
from app.services.audit import client_ip, write_audit
from app.services.imports import ImportRejected, build_preview, cancel_import, confirm_import, sample_template_csv, summary_message

router = APIRouter(tags=["Imports"])


def _owned_session(import_id: int, project_id: int, user_id: int, db) -> ImportSession:
    session = db.get(ImportSession, import_id)
    if session is None or session.project_id != project_id:
        raise HTTPException(status_code=404, detail="Import preview not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this import")
    return session


@router.get("/api/imports/sample-template")
def download_template(current: CurrentUser):
    content = sample_template_csv()
    if not content.endswith("\n"):
        content += "\n"
    header = "attachment; filename=\"costwise-import-template.csv\""
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": header, "X-Template-Note": SAMPLE_TEMPLATE_NOTE[:180]},
    )


@router.post("/api/projects/{project_id}/imports/preview", response_model=ImportPreviewOut)
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
async def preview_import(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    column_map: str | None = Form(default=None),
):
    project = get_owned_project(project_id, db, current, request)
    filename = file.filename or ""
    content = await file.read()
    mapping = None
    if column_map:
        try:
            parsed = json.loads(column_map)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Column mapping must be valid JSON.") from None
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=400, detail="Column mapping must be an object of fields to headers.")
        mapping = {str(key): str(value) for key, value in parsed.items()}
    try:
        preview = build_preview(db, project, current.id, filename, content, mapping)
    except ImportRejected as exc:
        write_audit("import_rejected", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id}")
        raise HTTPException(status_code=400, detail=exc.message) from None
    write_audit("import_previewed", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id}")
    return preview


@router.post("/api/projects/{project_id}/imports/confirm", response_model=ImportSummaryOut)
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
def confirm(
    project_id: int,
    payload: ImportConfirmIn,
    request: Request,
    current: CurrentUser,
    db: DbSession,
):
    get_owned_project(project_id, db, current, request)
    session = _owned_session(payload.import_id, project_id, current.id, db)
    confirmed = confirm_import(db, session)
    write_audit(
        "import_confirmed",
        user_id=current.id,
        ip_address=client_ip(request),
        detail=f"project_id={project_id} import_id={confirmed.id} rows={confirmed.imported_count}",
    )
    return ImportSummaryOut(
        import_id=confirmed.id,
        status=confirmed.status,
        accepted_count=confirmed.accepted_count,
        rejected_count=confirmed.rejected_count,
        duplicate_count=confirmed.duplicate_count,
        imported_count=confirmed.imported_count,
        message=summary_message(confirmed),
    )


@router.post("/api/projects/{project_id}/imports/{import_id}/cancel", response_model=ImportSummaryOut)
def cancel(project_id: int, import_id: int, request: Request, current: CurrentUser, db: DbSession):
    get_owned_project(project_id, db, current, request)
    session = _owned_session(import_id, project_id, current.id, db)
    cancelled = cancel_import(db, session)
    write_audit("import_cancelled", user_id=current.id, ip_address=client_ip(request), detail=f"import_id={import_id}")
    return ImportSummaryOut(
        import_id=cancelled.id,
        status=cancelled.status,
        accepted_count=cancelled.accepted_count,
        rejected_count=cancelled.rejected_count,
        duplicate_count=cancelled.duplicate_count,
        imported_count=cancelled.imported_count,
        message=summary_message(cancelled),
    )


@router.get("/api/projects/{project_id}/imports/{import_id}", response_model=ImportSummaryOut)
def get_import(project_id: int, import_id: int, request: Request, current: CurrentUser, db: DbSession):
    get_owned_project(project_id, db, current, request)
    session = _owned_session(import_id, project_id, current.id, db)
    return ImportSummaryOut(
        import_id=session.id,
        status=session.status,
        accepted_count=session.accepted_count,
        rejected_count=session.rejected_count,
        duplicate_count=session.duplicate_count,
        imported_count=session.imported_count,
        message=summary_message(session) + " " + DUPLICATE_POLICY,
    )
