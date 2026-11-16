"""Filtered cost summaries and chart series for one user's records."""

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.models import Expense, Project, User
from app.services.calculations import as_float, money, to_decimal, variance
from app.services.presenters import summary_out


def owned_projects(db: Session, user: User) -> list[Project]:
    return db.query(Project).filter(Project.owner_id == user.id).order_by(Project.id.asc()).all()


def select_currency(projects: list[Project], requested: str | None) -> tuple[str, list[str]]:
    present = sorted({project.currency for project in projects})
    if requested:
        return requested.upper(), present
    if "PKR" in present or not present:
        return "PKR", present
    return present[0], present


def filtered_expenses(
    db: Session,
    user: User,
    *,
    project_id: int | None = None,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    currency: str | None = None,
) -> list[Expense]:
    query = db.query(Expense).join(Project).filter(Project.owner_id == user.id)
    if project_id is not None:
        query = query.filter(Project.id == project_id)
    if currency:
        query = query.filter(Project.currency == currency)
    if category:
        query = query.filter(Expense.category == category)
    if date_from is not None:
        query = query.filter(Expense.expense_date >= date_from)
    if date_to is not None:
        query = query.filter(Expense.expense_date <= date_to)
    return query.order_by(Expense.expense_date.asc(), Expense.id.asc()).all()


def _point(label: str, estimated, actual) -> dict:
    difference = variance(actual, estimated)
    return {
        "label": label,
        "estimated": as_float(money(estimated)),
        "actual": as_float(money(actual)),
        "variance": as_float(difference),
    }


def build_charts(expenses: list[Expense], projects_by_id: dict[int, Project]) -> dict:
    by_category: dict[str, list] = defaultdict(lambda: [0, 0])
    by_project: dict[str, list] = defaultdict(lambda: [0, 0])
    by_month: dict[str, list] = defaultdict(lambda: [0, 0])
    for expense in expenses:
        estimated = to_decimal(expense.estimated_cost)
        actual = to_decimal(expense.actual_cost)
        by_category[expense.category][0] += estimated
        by_category[expense.category][1] += actual
        project = projects_by_id.get(expense.project_id)
        project_label = project.name if project else f"Project {expense.project_id}"
        by_project[project_label][0] += estimated
        by_project[project_label][1] += actual
        month = expense.expense_date.strftime("%Y-%m")
        by_month[month][0] += estimated
        by_month[month][1] += actual

    category_points = [_point(label, values[0], values[1]) for label, values in sorted(by_category.items())]
    project_points = [_point(label, values[0], values[1]) for label, values in sorted(by_project.items())]
    cumulative = 0
    timeline = []
    for label, values in sorted(by_month.items()):
        cumulative += values[1]
        timeline.append(
            {
                "label": label,
                "estimated": as_float(money(values[0])),
                "actual": as_float(money(values[1])),
                "cumulative_actual": as_float(money(cumulative)),
            }
        )
    distribution = [
        {"label": point["label"], "actual": point["actual"]}
        for point in category_points
        if point["actual"] > 0
    ]
    return {
        "by_category": category_points,
        "by_project": project_points,
        "variance_by_category": category_points,
        "spending_over_time": timeline,
        "category_distribution": distribution,
    }


def build_summary(expenses: list[Expense], currency: str, currencies_present: list[str]) -> dict:
    return summary_out(expenses, currency, currencies_present)
