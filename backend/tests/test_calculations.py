"""Cost calculation rules."""

from decimal import Decimal

from app.services.calculations import (
    budget_probability,
    percentage_variance,
    pert_expected,
    pert_std_dev,
    pert_variance,
    summarize,
    variance,
)
from app.services.reports import csv_safe as probe_csv_safe


def test_variance_signs():
    assert variance(150, 100) == Decimal("50.00")
    assert variance(80, 100) == Decimal("-20.00")
    assert variance(40, 40) == Decimal("0.00")


def test_percentage_variance_is_na_when_estimate_is_zero():
    assert percentage_variance(25, 0) is None


def test_aggregate_percentage_uses_totals_not_the_average_of_rows():
    summary = summarize(
        [
            {"estimated_cost": 10, "actual_cost": 40},
            {"estimated_cost": 1000, "actual_cost": 1000},
        ]
    )
    assert summary["percentage_variance"] == Decimal("2.97")
    assert summary["total_estimated"] == Decimal("1010.00")
    assert summary["total_actual"] == Decimal("1040.00")
    assert summary["over_budget_count"] == 1
    assert summary["on_budget_count"] == 1


def test_pert_expected_and_spread():
    assert pert_expected(6, 9, 18) == Decimal("10.00")
    assert pert_std_dev(6, 18) == Decimal("2.00")
    assert pert_variance(Decimal("2.00")) == Decimal("4.00")
    assert pert_expected(100, 120, 180) == Decimal("126.67")
    assert pert_std_dev(100, 180) == Decimal("13.33")
    assert budget_probability(Decimal("20.00"), Decimal("0.00"), Decimal("20")) == Decimal("100.00")
    assert budget_probability(Decimal("20.00"), Decimal("2.83"), Decimal("20")) == Decimal("50.00")


def test_csv_formula_guard_keeps_numeric_costs():
    assert probe_csv_safe(1500.5) == 1500.5
    assert probe_csv_safe(-20) == -20
    assert str(probe_csv_safe('=HYPERLINK("http://example.test")')).startswith("'")
    assert str(probe_csv_safe("+cmd")).startswith("'")
    assert str(probe_csv_safe("@SUM(A1)")).startswith("'")
    assert str(probe_csv_safe("-Vendor")).startswith("'")


def test_hosted_postgres_urls_use_psycopg_driver():
    from app.database import normalize_database_url

    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
