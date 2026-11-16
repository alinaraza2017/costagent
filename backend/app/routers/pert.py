"""PERT analysis and project comparison for the signed-in owner."""

from fastapi import APIRouter, HTTPException, Request

from app.deps import CurrentUser, DbSession, get_owned_project
from app.models import Expense
from app.schemas import CompareOut, PertOut
from app.services.audit import client_ip, write_audit
from app.services.comparison import compare_projects
from app.services.pert import analyze_pert, suggest_points

router = APIRouter(prefix="/api", tags=["PERT"])


def _expenses(db, project_id: int) -> list[Expense]:
    return db.query(Expense).filter(Expense.project_id == project_id).all()


@router.get("/projects/{project_id}/pert", response_model=PertOut)
def project_pert(project_id: int, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    return PertOut(**analyze_pert(project, _expenses(db, project.id)))


@router.post("/projects/{project_id}/pert/suggest", response_model=PertOut)
def suggest_project_pert(project_id: int, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    expenses = _expenses(db, project.id)
    suggested = 0
    for expense in expenses:
        if expense.optimistic_cost is not None and expense.most_likely_cost is not None and expense.pessimistic_cost is not None:
            continue
        optimistic, most_likely, pessimistic = suggest_points(expense.estimated_cost)
        expense.optimistic_cost = optimistic
        expense.most_likely_cost = most_likely
        expense.pessimistic_cost = pessimistic
        suggested += 1
    if suggested:
        db.commit()
        write_audit(
            "pert_suggested",
            user_id=current.id,
            ip_address=client_ip(request),
            detail=f"project_id={project.id} rows={suggested}",
        )
    payload = analyze_pert(project, _expenses(db, project.id))
    payload["suggested_count"] = suggested
    return PertOut(**payload)


@router.get("/analytics/compare", response_model=CompareOut)
def compare(
    left_id: int,
    right_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
):
    if left_id == right_id:
        raise HTTPException(status_code=422, detail="Choose two different projects")
    left = get_owned_project(left_id, db, current, request)
    right = get_owned_project(right_id, db, current, request)
    payload = compare_projects(left, _expenses(db, left.id), right, _expenses(db, right.id))
    return CompareOut(**payload)
