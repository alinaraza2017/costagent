"""Convert database rows into API dictionaries."""

from app.models import Expense, Project
from app.services.calculations import (
    as_float,
    interpret_variance,
    money,
    percentage_variance,
    pert_expected,
    pert_std_dev,
    summarize,
    to_decimal,
    variance,
)


def _pert_fields(expense: Expense) -> dict:
    points = (expense.optimistic_cost, expense.most_likely_cost, expense.pessimistic_cost)
    if any(point is None for point in points):
        return {
            "optimistic_cost": as_float(money(points[0])) if points[0] is not None else None,
            "most_likely_cost": as_float(money(points[1])) if points[1] is not None else None,
            "pessimistic_cost": as_float(money(points[2])) if points[2] is not None else None,
            "pert_expected": None,
            "pert_std_dev": None,
        }
    expected = pert_expected(*points)
    std_dev = pert_std_dev(points[0], points[2])
    return {
        "optimistic_cost": as_float(money(points[0])),
        "most_likely_cost": as_float(money(points[1])),
        "pessimistic_cost": as_float(money(points[2])),
        "pert_expected": as_float(expected),
        "pert_std_dev": as_float(std_dev),
    }


def expense_out(expense: Expense) -> dict:
    difference = variance(expense.actual_cost, expense.estimated_cost)
    percent = percentage_variance(expense.actual_cost, expense.estimated_cost)
    payload = {
        "id": expense.id,
        "project_id": expense.project_id,
        "expense_name": expense.expense_name,
        "category": expense.category,
        "description": expense.description or "",
        "estimated_cost": as_float(money(expense.estimated_cost)),
        "actual_cost": as_float(money(expense.actual_cost)),
        "variance": as_float(difference),
        "percentage_variance": as_float(percent) if percent is not None else None,
        "variance_interpretation": interpret_variance(difference),
        "expense_date": expense.expense_date,
        "vendor": expense.vendor,
        "created_at": expense.created_at,
        "updated_at": expense.updated_at,
    }
    payload.update(_pert_fields(expense))
    return payload


def summary_out(expenses: list[Expense], currency: str, currencies_present: list[str] | None = None) -> dict:
    rows = [
        {"estimated_cost": to_decimal(item.estimated_cost), "actual_cost": to_decimal(item.actual_cost)}
        for item in expenses
    ]
    summary = summarize(rows)
    present = currencies_present or [currency]
    return {
        "total_estimated": as_float(summary["total_estimated"]),
        "total_actual": as_float(summary["total_actual"]),
        "total_variance": as_float(summary["total_variance"]),
        "percentage_variance": as_float(summary["percentage_variance"]) if summary["percentage_variance"] is not None else None,
        "expense_count": summary["expense_count"],
        "over_budget_count": summary["over_budget_count"],
        "under_budget_count": summary["under_budget_count"],
        "on_budget_count": summary["on_budget_count"],
        "interpretation": summary["interpretation"],
        "currency": currency,
        "mixed_currencies": len(set(present)) > 1,
        "currencies_present": present,
    }


def project_out(project: Project, expenses: list[Expense], currencies_present: list[str] | None = None) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description or "",
        "start_date": project.start_date,
        "end_date": project.end_date,
        "budget": as_float(money(project.budget)),
        "currency": project.currency,
        "status": project.status,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "summary": summary_out(expenses, project.currency, currencies_present or [project.currency]),
    }
