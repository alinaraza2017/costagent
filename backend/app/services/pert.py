"""PERT three-point cost analysis for one owned project."""

from decimal import Decimal

from app.models import Expense, Project
from app.services.calculations import (
    as_float,
    budget_probability,
    money,
    pert_expected,
    pert_std_dev,
    pert_variance,
    to_decimal,
)

SUGGEST_OPTIMISTIC = Decimal("0.90")
SUGGEST_MOST_LIKELY = Decimal("1")
SUGGEST_PESSIMISTIC = Decimal("1.25")

PERT_ASSUMPTION = (
    "Expected cost is (optimistic + 4 x most likely + pessimistic) / 6. "
    "Each activity's standard deviation is (pessimistic - optimistic) / 6. "
    "The project standard deviation is the square root of the sum of activity variances, "
    "which treats the activities as independent. "
    "The budget chance uses a normal curve around the expected cost. "
    "Ranges are not shown below zero. These figures are a planning aid, not a guarantee."
)

SUGGEST_NOTE = (
    "Suggested values use 90% of the single estimate as optimistic, the estimate as most likely, "
    "and 125% of the estimate as pessimistic. Replace them when you have a real three-point judgment."
)


def suggest_points(estimated) -> tuple[Decimal, Decimal, Decimal]:
    amount = to_decimal(estimated)
    limit = Decimal("100000000000")
    optimistic = money(amount * SUGGEST_OPTIMISTIC)
    most_likely = money(amount * SUGGEST_MOST_LIKELY)
    pessimistic = money(amount * SUGGEST_PESSIMISTIC)
    if pessimistic > limit:
        pessimistic = limit
    if most_likely > pessimistic:
        most_likely = pessimistic
    if optimistic > most_likely:
        optimistic = most_likely
    return optimistic, most_likely, pessimistic


def _complete(expense: Expense) -> bool:
    return (
        expense.optimistic_cost is not None
        and expense.most_likely_cost is not None
        and expense.pessimistic_cost is not None
    )


def _band(expected: Decimal, std_dev: Decimal, multiplier: int) -> dict:
    low = money(expected - (std_dev * Decimal(multiplier)))
    high = money(expected + (std_dev * Decimal(multiplier)))
    if low < 0:
        low = Decimal("0.00")
    labels = {1: "About 68%", 2: "About 95%", 3: "About 99.7%"}
    return {
        "label": labels[multiplier],
        "low": as_float(low),
        "high": as_float(high),
    }


def analyze_pert(project: Project, expenses: list[Expense]) -> dict:
    activities = []
    missing = []
    total_expected = Decimal("0")
    total_variance = Decimal("0")
    ordered = sorted(expenses, key=lambda item: (item.expense_date, item.id))
    for expense in ordered:
        if not _complete(expense):
            missing.append(
                {
                    "expense_id": expense.id,
                    "expense_name": expense.expense_name,
                    "estimated_cost": as_float(money(expense.estimated_cost)),
                }
            )
            continue
        expected = pert_expected(expense.optimistic_cost, expense.most_likely_cost, expense.pessimistic_cost)
        std_dev = pert_std_dev(expense.optimistic_cost, expense.pessimistic_cost)
        variance = pert_variance(std_dev)
        total_expected += expected
        total_variance += variance
        activities.append(
            {
                "expense_id": expense.id,
                "expense_name": expense.expense_name,
                "category": expense.category,
                "optimistic_cost": as_float(money(expense.optimistic_cost)),
                "most_likely_cost": as_float(money(expense.most_likely_cost)),
                "pessimistic_cost": as_float(money(expense.pessimistic_cost)),
                "expected_cost": as_float(expected),
                "std_dev": as_float(std_dev),
                "variance": as_float(variance),
            }
        )
    if activities:
        expected_total = money(total_expected)
        variance_total = money(total_variance)
        std_total = money(total_variance.sqrt())
        chance = budget_probability(expected_total, std_total, project.budget)
        ranges = [_band(expected_total, std_total, step) for step in (1, 2, 3)]
    else:
        expected_total = None
        variance_total = None
        std_total = None
        chance = None
        ranges = []
    return {
        "project_id": project.id,
        "project_name": project.name,
        "currency": project.currency,
        "budget": as_float(money(project.budget)),
        "activity_count": len(activities),
        "missing_count": len(missing),
        "expected_cost": as_float(expected_total) if expected_total is not None else None,
        "std_dev": as_float(std_total) if std_total is not None else None,
        "variance": as_float(variance_total) if variance_total is not None else None,
        "budget_probability": as_float(chance) if chance is not None else None,
        "ranges": ranges,
        "activities": activities,
        "missing": missing,
        "assumption": PERT_ASSUMPTION,
        "suggest_note": SUGGEST_NOTE,
    }
