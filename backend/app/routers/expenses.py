"""Expense routes nested under projects, with ownership checks."""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Query, Request, Response

from app.deps import CurrentUser, DbSession, get_owned_expense, get_owned_project
from app.models import Expense
from app.schemas import ExpenseInput, ExpenseOut, ExpensePage
from app.services.audit import client_ip, write_audit
from app.services.calculations import money
from app.services.presenters import expense_out

router = APIRouter(tags=["Expenses"])


@router.get("/api/projects/{project_id}/expenses", response_model=ExpensePage)
def list_expenses(
    project_id: int,
    request: Request,
    current: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    project = get_owned_project(project_id, db, current, request)
    query = db.query(Expense).filter(Expense.project_id == project.id)
    if category:
        query = query.filter(Expense.category == category)
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    total = query.count()
    rows = query.order_by(Expense.expense_date.desc(), Expense.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ExpensePage(items=[ExpenseOut(**expense_out(row)) for row in rows], total=total, page=page, page_size=page_size)


@router.post("/api/projects/{project_id}/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(project_id: int, payload: ExpenseInput, request: Request, current: CurrentUser, db: DbSession):
    project = get_owned_project(project_id, db, current, request)
    expense = Expense(
        project_id=project.id,
        expense_name=payload.expense_name,
        category=payload.category,
        description=payload.description,
        estimated_cost=money(payload.estimated_cost),
        actual_cost=money(payload.actual_cost),
        optimistic_cost=money(payload.optimistic_cost) if payload.optimistic_cost is not None else None,
        most_likely_cost=money(payload.most_likely_cost) if payload.most_likely_cost is not None else None,
        pessimistic_cost=money(payload.pessimistic_cost) if payload.pessimistic_cost is not None else None,
        expense_date=payload.expense_date,
        vendor=payload.vendor,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    write_audit("expense_created", user_id=current.id, ip_address=client_ip(request), detail=f"expense_id={expense.id}")
    return ExpenseOut(**expense_out(expense))


@router.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, payload: ExpenseInput, request: Request, current: CurrentUser, db: DbSession):
    expense = get_owned_expense(expense_id, db, current, request)
    expense.expense_name = payload.expense_name
    expense.category = payload.category
    expense.description = payload.description
    expense.estimated_cost = money(payload.estimated_cost)
    expense.actual_cost = money(payload.actual_cost)
    expense.optimistic_cost = money(payload.optimistic_cost) if payload.optimistic_cost is not None else None
    expense.most_likely_cost = money(payload.most_likely_cost) if payload.most_likely_cost is not None else None
    expense.pessimistic_cost = money(payload.pessimistic_cost) if payload.pessimistic_cost is not None else None
    expense.expense_date = payload.expense_date
    expense.vendor = payload.vendor
    expense.updated_at = datetime.now(timezone.utc)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    write_audit("expense_updated", user_id=current.id, ip_address=client_ip(request), detail=f"expense_id={expense.id}")
    return ExpenseOut(**expense_out(expense))


@router.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: int, request: Request, current: CurrentUser, db: DbSession):
    expense = get_owned_expense(expense_id, db, current, request)
    db.delete(expense)
    db.commit()
    write_audit("expense_deleted", user_id=current.id, ip_address=client_ip(request), detail=f"expense_id={expense_id}")
    return Response(status_code=204)
