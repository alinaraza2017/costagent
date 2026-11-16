"""Project routes. Ownership is checked on the server."""

from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy.orm import Session

from app.deps import CurrentUser, DbSession, get_owned_project
from app.models import Expense, Project
from app.schemas import ProjectInput, ProjectOut, ProjectPage
from app.services.audit import client_ip, write_audit
from app.services.calculations import money
from app.services.presenters import project_out

router = APIRouter(prefix="/api/projects", tags=["Projects"])


def _load_expenses_by_project(db: Session, project_ids: list[int]) -> dict[int, list[Expense]]:
    grouped: dict[int, list[Expense]] = {project_id: [] for project_id in project_ids}
    if not project_ids:
        return grouped
    expenses = db.query(Expense).filter(Expense.project_id.in_(project_ids)).all()
    for expense in expenses:
        grouped.setdefault(expense.project_id, []).append(expense)
    return grouped


@router.get("", response_model=ProjectPage)
def list_projects(
    current: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Project).filter(Project.owner_id == current.id)
    total = query.count()
    projects = query.order_by(Project.updated_at.desc(), Project.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    grouped = _load_expenses_by_project(db, [project.id for project in projects])
    currencies = sorted({project.currency for project in db.query(Project).filter(Project.owner_id == current.id).all()})
    return ProjectPage(
        items=[ProjectOut(**project_out(project, grouped.get(project.id, []), currencies or [project.currency])) for project in projects],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectInput, request: Request, current: CurrentUser, db: DbSession):
    project = Project(
        owner_id=current.id,
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
        end_date=payload.end_date,
        budget=money(payload.budget),
        currency=payload.currency,
        status=payload.status,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    write_audit("project_created", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id}")
    return ProjectOut(**project_out(project, []))


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    expenses = db.query(Expense).filter(Expense.project_id == project.id).all()
    return ProjectOut(**project_out(project, expenses))


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, payload: ProjectInput, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    project.name = payload.name
    project.description = payload.description
    project.start_date = payload.start_date
    project.end_date = payload.end_date
    project.budget = money(payload.budget)
    project.currency = payload.currency
    project.status = payload.status
    project.updated_at = datetime.now(timezone.utc)
    db.add(project)
    db.commit()
    db.refresh(project)
    expenses = db.query(Expense).filter(Expense.project_id == project.id).all()
    write_audit("project_updated", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project.id}")
    return ProjectOut(**project_out(project, expenses))


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    db.delete(project)
    db.commit()
    write_audit("project_deleted", user_id=current.id, ip_address=client_ip(request), detail=f"project_id={project_id}")
    return Response(status_code=204)
