"""Authoritative cost calculations.

Percentage variance uses aggregate estimated and actual totals.
It is not the average of per-expense percentages.
"""

import math
from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")
PERCENT = Decimal("0.01")


def to_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value) -> Decimal:
    return to_decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def variance(actual, estimated) -> Decimal:
    return money(to_decimal(actual) - to_decimal(estimated))


def percentage_variance(actual, estimated):
    estimated_amount = to_decimal(estimated)
    if estimated_amount == 0:
        return None
    actual_amount = to_decimal(actual)
    raw = ((actual_amount - estimated_amount) / estimated_amount) * Decimal("100")
    return raw.quantize(PERCENT, rounding=ROUND_HALF_UP)


def interpret_variance(amount: Decimal) -> str:
    if amount > 0:
        return "Actual cost exceeded the estimate"
    if amount < 0:
        return "Actual cost was below the estimate"
    return "Actual cost matched the estimate"


def summarize(rows: list[dict]) -> dict:
    """Summarize expense dictionaries that contain estimated_cost and actual_cost."""
    total_estimated = Decimal("0")
    total_actual = Decimal("0")
    over_budget = 0
    under_budget = 0
    on_budget = 0
    for row in rows:
        estimated = to_decimal(row["estimated_cost"])
        actual = to_decimal(row["actual_cost"])
        total_estimated += estimated
        total_actual += actual
        difference = actual - estimated
        if difference > 0:
            over_budget += 1
        elif difference < 0:
            under_budget += 1
        else:
            on_budget += 1
    total_variance = money(total_actual - total_estimated)
    return {
        "total_estimated": money(total_estimated),
        "total_actual": money(total_actual),
        "total_variance": total_variance,
        "percentage_variance": percentage_variance(total_actual, total_estimated),
        "expense_count": len(rows),
        "over_budget_count": over_budget,
        "under_budget_count": under_budget,
        "on_budget_count": on_budget,
        "interpretation": interpret_variance(total_variance) if rows else "No expenses in this selection",
    }


def as_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def pert_expected(optimistic, most_likely, pessimistic) -> Decimal:
    """Classic PERT expected cost: (O + 4M + P) / 6."""
    raw = (
        to_decimal(optimistic) + (Decimal(4) * to_decimal(most_likely)) + to_decimal(pessimistic)
    ) / Decimal(6)
    return money(raw)


def pert_std_dev(optimistic, pessimistic) -> Decimal:
    """PERT standard deviation: (P - O) / 6."""
    raw = (to_decimal(pessimistic) - to_decimal(optimistic)) / Decimal(6)
    return money(raw)


def pert_variance(std_dev) -> Decimal:
    return money(to_decimal(std_dev) ** 2)


def normal_cdf_percent(z: float) -> Decimal:
    """Percent chance from a standard-normal z score, rounded to two decimals."""
    probability = Decimal(str(0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))))
    return (probability * Decimal(100)).quantize(PERCENT, rounding=ROUND_HALF_UP)


def budget_probability(expected, std_dev, budget) -> Decimal:
    """Chance that a normal cost centered on the PERT expected value stays within budget."""
    expected_amount = to_decimal(expected)
    spread = to_decimal(std_dev)
    target = to_decimal(budget)
    if spread == 0:
        return Decimal("100.00") if expected_amount <= target else Decimal("0.00")
    z_score = float((target - expected_amount) / spread)
    return normal_cdf_percent(z_score)


def linear_quantile(sorted_values: list[float], quantile: float) -> float:
    count = len(sorted_values)
    if count == 0:
        raise ValueError("At least one value is required")
    if count == 1:
        return float(sorted_values[0])
    position = (count - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, count - 1)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction
