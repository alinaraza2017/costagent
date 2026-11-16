"""Dashboard and chart data computed from the caller's records."""

from datetime import date

from fastapi import APIRouter, Query, Request

from app.constants import CATEGORIES
from app.deps import CurrentUser, DbSession, get_owned_project
from app.models import Project
from app.schemas import ChartsOut, SummaryOut
from app.services.analytics import build_charts, build_summary, filtered_expenses, owned_projects, select_currency

router = APIRouter(prefix="/api", tags=["Analytics"])


def _prepare(
    db,
    user,
    request: Request,
    project_id: int | None,
    category: str | None,
    date_from: date | None,
    date_to: date | None,
    currency: str | None,
):
    if category and category not in CATEGORIES:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="Select a supported category")
    projects = owned_projects(db, user)
    if project_id is not None:
        get_owned_project(project_id, db, user, request)
        projects = [project for project in projects if project.id == project_id]
    selected, present = select_currency(projects, currency)
    expenses = filtered_expenses(
        db,
        user,
        project_id=project_id,
        category=category,
        date_from=date_from,
        date_to=date_to,
        currency=selected,
    )
    return projects, expenses, selected, present


@router.get("/analytics/summary", response_model=SummaryOut)
def summary(
    request: Request,
    current: CurrentUser,
    db: DbSession,
    project_id: int | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    currency: str | None = None,
):
    _projects, expenses, selected, present = _prepare(db, current, request, project_id, category, date_from, date_to, currency)
    return SummaryOut(**build_summary(expenses, selected, present))


@router.get("/analytics/charts", response_model=ChartsOut)
def charts(
    request: Request,
    current: CurrentUser,
    db: DbSession,
    project_id: int | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    currency: str | None = None,
):
    projects, expenses, selected, _present = _prepare(db, current, request, project_id, category, date_from, date_to, currency)
    projects_by_id = {project.id: project for project in projects}
    if project_id is not None and project_id not in projects_by_id:
        project = db.get(Project, project_id)
        if project is not None:
            projects_by_id[project.id] = project
    payload = build_charts(expenses, projects_by_id)
    payload["currency"] = selected
    return ChartsOut(**payload)


@router.get("/projects/{project_id}/analytics", response_model=SummaryOut)
def project_summary(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    return summary(request, current, db, project_id, category, date_from, date_to, None)


@router.get("/projects/{project_id}/charts", response_model=ChartsOut)
def project_charts(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    category: str | None = Query(default=None),
    date_from: date | None = None,
    date_to: date | None = None,
):
    return charts(request, current, db, project_id, category, date_from, date_to, None)
