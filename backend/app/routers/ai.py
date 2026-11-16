"""AI and rule-based cost analysis."""

from fastapi import APIRouter, Request

from app.config import get_settings
from app.deps import CurrentUser, DbSession, get_owned_project
from app.limiter import limiter
from app.models import Expense
from app.schemas import AnalysisOut
from app.services.ai_analysis import analyze_project
from app.services.audit import client_ip, write_audit

router = APIRouter(tags=["AI"])


@router.post("/api/projects/{project_id}/ai/analyze", response_model=AnalysisOut)
@limiter.limit(lambda: get_settings().sensitive_rate_limit)
def analyze(project_id: int, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    expenses = db.query(Expense).filter(Expense.project_id == project.id).order_by(Expense.expense_date.asc()).all()
    result = analyze_project(project, expenses)
    write_audit(
        "analysis_requested",
        user_id=current.id,
        ip_address=client_ip(request),
        detail=f"project_id={project.id} mode={result['mode']}",
    )
    return result
