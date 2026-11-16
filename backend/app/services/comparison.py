"""Side-by-side comparison of two projects owned by the same user."""

from collections import defaultdict
from decimal import Decimal

from app.models import Expense, Project
from app.services.calculations import as_float, money, percentage_variance, to_decimal, variance
from app.services.pert import analyze_pert


def _category_totals(expenses: list[Expense]) -> dict[str, dict[str, Decimal]]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"estimated": Decimal("0"), "actual": Decimal("0")}
    )
    for expense in expenses:
        bucket = totals[expense.category]
        bucket["estimated"] += to_decimal(expense.estimated_cost)
        bucket["actual"] += to_decimal(expense.actual_cost)
    return totals


def _money_delta(right, left):
    if right is None or left is None:
        return None
    return as_float(money(to_decimal(right) - to_decimal(left)))


def project_side(project: Project, expenses: list[Expense]) -> dict:
    estimated = money(sum((to_decimal(item.estimated_cost) for item in expenses), Decimal("0")))
    actual = money(sum((to_decimal(item.actual_cost) for item in expenses), Decimal("0")))
    difference = variance(actual, estimated)
    pert = analyze_pert(project, expenses)
    categories = _category_totals(expenses)
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "currency": project.currency,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "budget": as_float(money(project.budget)),
        "expense_count": len(expenses),
        "total_estimated": as_float(estimated),
        "total_actual": as_float(actual),
        "total_variance": as_float(difference),
        "percentage_variance": as_float(percentage_variance(actual, estimated)),
        "pert_expected": pert["expected_cost"],
        "pert_std_dev": pert["std_dev"],
        "pert_activity_count": pert["activity_count"],
        "pert_missing_count": pert["missing_count"],
        "categories": [
            {
                "category": name,
                "estimated": as_float(money(amounts["estimated"])),
                "actual": as_float(money(amounts["actual"])),
            }
            for name, amounts in sorted(categories.items())
        ],
    }


def compare_projects(
    left_project: Project,
    left_expenses: list[Expense],
    right_project: Project,
    right_expenses: list[Expense],
) -> dict:
    left = project_side(left_project, left_expenses)
    right = project_side(right_project, right_expenses)
    same_currency = left_project.currency == right_project.currency
    notes = [
        "Differences are the second project minus the first project.",
        "Percentage variance on each side uses that project's own estimated and actual totals.",
    ]
    deltas = None
    if same_currency:
        deltas = {
            "budget": _money_delta(right["budget"], left["budget"]),
            "total_estimated": _money_delta(right["total_estimated"], left["total_estimated"]),
            "total_actual": _money_delta(right["total_actual"], left["total_actual"]),
            "total_variance": _money_delta(right["total_variance"], left["total_variance"]),
            "pert_expected": _money_delta(right["pert_expected"], left["pert_expected"]),
        }
    else:
        notes.append(
            f"{left_project.name} is in {left_project.currency} and {right_project.name} is in {right_project.currency}. "
            "Amounts are shown in their own currencies and are not subtracted."
        )
    names = sorted({row["category"] for row in left["categories"]} | {row["category"] for row in right["categories"]})
    left_by_name = {row["category"]: row for row in left["categories"]}
    right_by_name = {row["category"]: row for row in right["categories"]}
    category_rows = []
    for name in names:
        left_row = left_by_name.get(name)
        right_row = right_by_name.get(name)
        category_rows.append(
            {
                "category": name,
                "left_estimated": left_row["estimated"] if left_row else 0,
                "left_actual": left_row["actual"] if left_row else 0,
                "right_estimated": right_row["estimated"] if right_row else 0,
                "right_actual": right_row["actual"] if right_row else 0,
            }
        )
    return {
        "same_currency": same_currency,
        "left": left,
        "right": right,
        "deltas": deltas,
        "category_rows": category_rows,
        "notes": notes,
    }
