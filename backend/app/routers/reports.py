"""Authorized PDF and CSV downloads."""

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import get_settings
from app.deps import CurrentUser, DbSession, get_owned_project
from app.limiter import limiter
from app.services.analytics import filtered_expenses
from app.services.audit import client_ip, write_audit
from app.services.reports import build_csv, build_pdf

router = APIRouter(tags=["Reports"])


def _expenses(db, user, project, category: str | None, date_from: date | None, date_to: date | None):
    return filtered_expenses(
        db,
        user,
        project_id=project.id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        currency=project.currency,
    )


@router.get("/api/projects/{project_id}/reports/pdf")
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
def pdf_report(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    project = get_owned_project(project_id, db, current, request)
    expenses = _expenses(db, current, project, category, date_from, date_to)
    content = build_pdf(project, expenses, date_from=date_from, date_to=date_to, category=category)
    write_audit("report_exported", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id} format=pdf")
    filename = f"costwise-project-{project.id}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/projects/{project_id}/reports/csv")
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
def csv_report(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    project = get_owned_project(project_id, db, current, request)
    expenses = _expenses(db, current, project, category, date_from, date_to)
    content = build_csv(project, expenses)
    write_audit("report_exported", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id} format=csv")
    filename = f"costwise-project-{project.id}.csv"
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
