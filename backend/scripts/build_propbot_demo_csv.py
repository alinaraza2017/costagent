"""Lab-demo PropBot CSV. Figures come from the SPMP workbook earned-value sheet."""

import csv
from decimal import Decimal
from pathlib import Path

from app.services.calculations import budget_probability, money, pert_expected, pert_std_dev, pert_variance

DOWNLOAD = Path(r"d:\downloads\PropBot_Lab_Demo.csv")
SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "PropBot_Lab_Demo.csv"

# name, category, estimate, actual, date, vendor, optimistic days, likely days, pessimistic days, note
# Day counts scale the labour estimate into a three-point cost. Non-labour uses 1, 1, 1.
LABOUR = [
    ("Project kickoff", "Personnel", 165000, 165000, "2026-04-21", "Project Manager", 4, 5, 8, "WBS 1.1. Finished on budget."),
    ("Requirement elicitation", "Personnel", 90000, 90000, "2026-04-28", "Business Analyst", 4, 5, 8, "WBS 1.2. Finished on budget."),
    ("Feasibility and model selection", "Personnel", 225000, 225000, "2026-05-05", "AI Developer", 4, 5, 8, "WBS 1.3. Finished on budget."),
    ("Scope and requirement specification", "Personnel", 165000, 165000, "2026-05-12", "Business Analyst", 4, 5, 8, "WBS 1.4. Finished on budget."),
    ("System architecture", "Personnel", 300000, 324000, "2026-06-02", "Software Architect", 12, 15, 22, "WBS 3.1. Finished over the estimate. Variance = 324000 - 300000."),
    ("Database schema", "Personnel", 220000, 231000, "2026-06-16", "Backend Developer", 8, 10, 15, "WBS 3.2. Finished over the estimate. Variance = 231000 - 220000."),
    ("UI wireframes", "Personnel", 270000, 270000, "2026-06-23", "Frontend Developer", 12, 15, 22, "WBS 3.3. Finished on budget."),
    ("FastAPI auth and roles", "Personnel", 330000, 346000, "2026-07-14", "Backend Developer", 12, 15, 22, "WBS 5.1.1. Finished over the estimate. Variance = 346000 - 330000."),
    ("Project vault backend", "Personnel", 440000, 484000, "2026-08-11", "Backend Developer", 16, 20, 30, "WBS 5.1.2. Finished over the estimate. Variance = 484000 - 440000."),
    ("RFP parser", "Personnel", 625000, 700000, "2026-09-15", "AI Developer", 20, 25, 38, "WBS 5.2.1. Finished over the estimate. Variance = 700000 - 625000."),
    ("Compliance matrix", "Personnel", 440000, 418000, "2026-10-13", "Backend Developer", 16, 20, 30, "WBS 5.2.2. Finished under the estimate. Variance = 418000 - 440000."),
    ("RAG pipeline earned by 25 Oct 2026", "Personnel", 525000, 604000, "2026-10-27", "AI Developer", 24, 30, 45, "WBS 5.2.3 is 70 percent complete. Full budget is 750000. This estimate is the earned value, 525000. Actual spend is 604000."),
    ("RAG pipeline not yet earned", "Personnel", 225000, 225000, "2026-10-27", "AI Developer", 24, 30, 45, "WBS 5.2.3 remainder. Not earned by 25 Oct 2026, so actual is kept equal to this remaining estimate."),
    ("HLD diagrams earned by 25 Oct 2026", "Personnel", 108000, 108000, "2026-11-03", "Frontend Developer", 12, 15, 22, "WBS 5.2.4 is 40 percent complete. Full budget is 270000. Spend matches the earned value."),
    ("HLD diagrams not yet earned", "Personnel", 162000, 162000, "2026-11-03", "Frontend Developer", 12, 15, 22, "WBS 5.2.4 remainder. Actual is kept equal to the remaining estimate."),
    ("React frontend", "Personnel", 360000, 360000, "2026-12-01", "Frontend Developer", 16, 20, 30, "WBS 5.3.1. Not started by 25 Oct 2026. Actual is kept equal to the estimate."),
    ("Export engines", "Personnel", 330000, 330000, "2026-12-22", "Backend Developer", 12, 15, 22, "WBS 5.3.2. Not started. Actual is kept equal to the estimate."),
    ("Integration testing", "Personnel", 180000, 180000, "2027-01-05", "QA Engineer", 8, 10, 15, "WBS 7.1. Not started. Actual is kept equal to the estimate."),
    ("RAGAS evaluation labour", "Personnel", 250000, 250000, "2027-01-19", "AI Developer", 8, 10, 15, "WBS 7.2. Not started. Actual is kept equal to the estimate."),
    ("User acceptance testing labour", "Personnel", 180000, 180000, "2027-01-26", "QA Engineer", 4, 5, 8, "WBS 7.3. Not started. Actual is kept equal to the estimate."),
    ("Bug fixes", "Personnel", 235000, 235000, "2027-02-02", "Backend Developer", 4, 5, 8, "WBS 7.4. Not started. Actual is kept equal to the estimate."),
    ("Docker deployment and documentation", "Personnel", 148000, 148000, "2027-02-08", "Backend Developer", 3, 4, 6, "WBS 8.1. Not started. Actual is kept equal to the estimate."),
    ("Final presentation", "Personnel", 30000, 30000, "2027-02-10", "Project Manager", 2, 2, 3, "WBS 8.2. Not started. Actual is kept equal to the estimate."),
]

OTHER = [
    ("Open-source tools", "Software & Tools", 0, 0, "2026-04-15", "Open-source / internal", "VS Code, GitHub, Jira, and the open-source stack. Estimate is 0, so percentage variance is N/A."),
    ("GPT-4o-mini input tokens", "AI / Cloud API", "4200", "4200", "2026-08-12", "OpenAI", "10 million tokens a month for 10 months at 0.15 USD, converted at 280 PKR per USD."),
    ("GPT-4o-mini output tokens", "AI / Cloud API", "3360", "3360", "2026-08-12", "OpenAI", "2 million tokens a month for 10 months at 0.60 USD, converted at 280 PKR per USD."),
    ("Embedding tokens", "AI / Cloud API", "280", "280", "2026-08-12", "OpenAI", "5 million tokens a month for 10 months at 0.02 USD, converted at 280 PKR per USD."),
    ("Prepaid API credit", "AI / Cloud API", "5600", "5600", "2026-08-12", "OpenAI", "One 20 USD top-up converted at 280 PKR per USD."),
    ("Developer laptops, existing", "Hardware & Infrastructure", "208333.33", "208333.33", "2026-04-15", "Estimated / To be confirmed", "Depreciation of 3 laptops over the 10 project months. Not a new purchase."),
    ("On-premise server, existing", "Hardware & Infrastructure", "62500", "62500", "2026-04-15", "Estimated / To be confirmed", "Depreciation of the existing server over the 10 project months."),
    ("Android test phone", "Hardware & Infrastructure", "25000", "25000", "2026-04-15", "Estimated / To be confirmed", "Depreciation of one test phone over the 10 project months."),
    ("Internet", "Hardware & Infrastructure", "150000", "150000", "2026-04-15", "Estimated / To be confirmed", "5000 PKR a month for each of 3 members, for 10 months."),
    ("Electricity", "Hardware & Infrastructure", "90000", "90000", "2026-04-15", "Estimated / To be confirmed", "3000 PKR a month for each of 3 members, for 10 months."),
    ("Backup SSD", "Hardware & Infrastructure", "18000", "18000", "2026-04-15", "Estimated / To be confirmed", "One 1 TB backup drive."),
    ("RAGAS API budget", "Testing", "4200", "4200", "2026-12-23", "Estimated / To be confirmed", "15 USD evaluation budget converted at 280 PKR per USD. Testing has not started."),
    ("UAT travel", "Testing", "8000", "8000", "2027-01-20", "Estimated / To be confirmed", "Four trips at 2000 PKR. UAT has not started."),
    ("Requirement travel", "Documentation & Handover", "6000", "6000", "2026-04-22", "Estimated / To be confirmed", "Three elicitation trips at 2000 PKR."),
    ("Printing and binding", "Documentation & Handover", "15000", "15000", "2027-02-03", "Estimated / To be confirmed", "Six bound copies at 2500 PKR."),
    ("Demo-day poster", "Documentation & Handover", "6000", "6000", "2027-02-09", "Estimated / To be confirmed", "Poster and demo-day material."),
]


def scaled_points(estimate: Decimal, optimistic_days, likely_days, pessimistic_days):
    """Turn the schedule's optimistic and pessimistic durations into costs for this row."""
    optimistic = money(estimate * Decimal(optimistic_days) / Decimal(likely_days))
    most_likely = money(estimate)
    pessimistic = money(estimate * Decimal(pessimistic_days) / Decimal(likely_days))
    if optimistic > most_likely:
        optimistic = most_likely
    if pessimistic < most_likely:
        pessimistic = most_likely
    return optimistic, most_likely, pessimistic


def main() -> None:
    rows = []
    for name, category, estimate, actual, expense_date, vendor, optimistic_days, likely_days, pessimistic_days, note in LABOUR:
        estimate_amount = money(estimate)
        actual_amount = money(actual)
        # RAG and HLD slices: day ratios apply to this row's own estimate.
        optimistic, most_likely, pessimistic = scaled_points(estimate_amount, optimistic_days, likely_days, pessimistic_days)
        rows.append([name, category, note, estimate_amount, actual_amount, expense_date, vendor, optimistic, most_likely, pessimistic])
    for name, category, estimate, actual, expense_date, vendor, note in OTHER:
        estimate_amount = money(estimate)
        actual_amount = money(actual)
        rows.append([name, category, note, estimate_amount, actual_amount, expense_date, vendor, estimate_amount, estimate_amount, estimate_amount])

    expected = Decimal("0")
    variance_sum = Decimal("0")
    estimated = Decimal("0")
    actual = Decimal("0")
    for row in rows:
        estimated += row[3]
        actual += row[4]
        activity_expected = pert_expected(row[7], row[8], row[9])
        activity_sigma = pert_std_dev(row[7], row[9])
        variance_sum += pert_variance(activity_sigma)
        expected += activity_expected
        assert row[7] <= row[8] <= row[9], row[0]
    expected = money(expected)
    spread = money(variance_sum.sqrt())
    suggested = money(expected + spread)
    chance = budget_probability(expected, spread, suggested)

    header = [
        "expense_name",
        "category",
        "description",
        "estimated_cost",
        "actual_cost",
        "expense_date",
        "vendor",
        "optimistic_cost",
        "most_likely_cost",
        "pessimistic_cost",
    ]
    for path in (DOWNLOAD, SAMPLE):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            for row in rows:
                writer.writerow([row[0], row[1], row[2], f"{row[3]:f}", f"{row[4]:f}", row[5], row[6], f"{row[7]:f}", f"{row[8]:f}", f"{row[9]:f}"])
    print("rows", len(rows))
    print("estimated", money(estimated))
    print("actual", money(actual))
    print("cost_variance", money(actual - estimated))
    print("pert_expected", expected)
    print("pert_std", spread)
    print("suggested_budget", suggested)
    print("chance_at_suggested", chance)


if __name__ == "__main__":
    main()
