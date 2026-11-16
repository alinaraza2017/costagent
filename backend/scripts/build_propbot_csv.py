"""Rebuild the PropBot CostWise import from the SPMP workbook figures. One-off writer."""

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

MONEY = Decimal("0.01")
OUT = Path(r"d:\downloads\PropBot_Costwise_Import.csv")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY, rounding=ROUND_HALF_UP)


def pert_costs(bac: Decimal, optimistic_days, likely_days, pessimistic_days):
    likely = Decimal(likely_days)
    optimistic = money(bac * Decimal(optimistic_days) / likely)
    most_likely = money(bac)
    pessimistic = money(bac * Decimal(pessimistic_days) / likely)
    return optimistic, most_likely, pessimistic


LABOUR = [
    # name, wbs, finish, bac, workbook actual, percent complete, resources, O, M, P, state
    ("Project Kickoff & Initial Stakeholder Meetings", "1.1", "2026-04-21", 165000, 165000, 1, "Project Manager, Business Analyst", 4, 5, 8, "complete"),
    ("Requirement Elicitation (NETS Engineer Interviews)", "1.2", "2026-04-28", 90000, 90000, 1, "Business Analyst", 4, 5, 8, "complete"),
    ("Feasibility Study & AI Model Selection (GPT-4o-mini)", "1.3", "2026-05-05", 225000, 225000, 1, "AI Developer, Software Architect", 4, 5, 8, "complete"),
    ("Final Scope Document & Requirement Specification", "1.4", "2026-05-12", 165000, 165000, 1, "Business Analyst, Technical Writer", 4, 5, 8, "complete"),
    ("System Architecture & Pipeline Flow (LangGraph)", "3.1", "2026-06-02", 300000, 324000, 1, "Software Architect", 12, 15, 22, "complete"),
    ("Database Schema (PostgreSQL & ChromaDB Vector Store)", "3.2", "2026-06-16", 220000, 231000, 1, "Backend Developer", 8, 10, 15, "complete"),
    ("UI/UX Wireframes & TipTap Editor Mockups", "3.3", "2026-06-23", 270000, 270000, 1, "Frontend Developer", 12, 15, 22, "complete"),
    ("FastAPI Setup, JWT Auth, and Role Management", "5.1.1", "2026-07-14", 330000, 346000, 1, "Backend Developer", 12, 15, 22, "complete"),
    ("Project Vault & Centralised Storage Backend", "5.1.2", "2026-08-11", 440000, 484000, 1, "Backend Developer", 16, 20, 30, "complete"),
    ("Module 1: RFP Parser & Section Classifier", "5.2.1", "2026-09-15", 625000, 700000, 1, "AI Developer", 20, 25, 38, "complete"),
    ("Module 3: Compliance Matrix Comparison Engine", "5.2.2", "2026-10-13", 440000, 418000, 1, "Backend Developer", 16, 20, 30, "complete"),
    ("Module 6: RAG Proposal Generation Pipeline", "5.2.3", "2026-10-27", 750000, 604000, "0.7", "AI Developer", 24, 30, 45, "progress"),
    ("Module 5: HLD Diagram & Written Connectivity", "5.2.4", "2026-11-03", 270000, 108000, "0.4", "Frontend Developer", 12, 15, 22, "progress"),
    ("React Frontend (Dashboards, Vault, & Search)", "5.3.1", "2026-12-01", 360000, 0, 0, "Frontend Developer", 16, 20, 30, "future"),
    ("Export Engines (DOCX, XLSX, Submission ZIP)", "5.3.2", "2026-12-22", 330000, 0, 0, "Backend Developer", 12, 15, 22, "future"),
    ("Internal Unit & Integration Testing", "7.1", "2027-01-05", 180000, 0, 0, "QA Engineer", 8, 10, 15, "future"),
    ("AI Performance Evaluation (RAGAS Metrics)", "7.2", "2027-01-19", 250000, 0, 0, "AI Developer", 8, 10, 15, "future"),
    ("User Acceptance Testing (UAT) with Engineers", "7.3", "2027-01-26", 180000, 0, 0, "QA Engineer, Business Analyst", 4, 5, 8, "future"),
    ("Bug Fixes & Final Optimisation", "7.4", "2027-02-02", 235000, 0, 0, "Backend Developer, AI Developer", 4, 5, 8, "future"),
    ("Local Docker Deployment & Documentation", "8.1", "2027-02-08", 148000, 0, 0, "Backend Developer, Technical Writer", 3, 4, 6, "future"),
    ("Final Project Presentation & Live Demo", "8.2", "2027-02-10", 30000, 0, 0, "Project Manager", 2, 2, 3, "future"),
]

NON_LABOUR = [
    ("VS Code, Python 3.11, Git", "Software & Tools", "Free development tools from the workbook Non_Labour sheet. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("GitHub (Free plan)", "Software & Tools", "Free version control. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("Jira / ClickUp free tier", "Software & Tools", "Free task tracking. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("Microsoft Project Professional", "Software & Tools", "University lab licence assumed in the workbook. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("FastAPI, PostgreSQL, ChromaDB, LangChain/LangGraph, React, TipTap, Docker", "Software & Tools", "Open-source stack. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("draw.io / Mermaid.js", "Software & Tools", "Free diagram tools. Planned cost is zero.", 0, "2026-04-15", "Open-source / internal"),
    ("GPT-4o-mini input tokens (M tokens/month)", "AI / Cloud API", "Workbook assumption: 10 million tokens a month at 0.15 USD, for 10 months, at 280 PKR per USD. No separate actual was recorded.", "4200", "2026-08-12", "OpenAI"),
    ("GPT-4o-mini output tokens (M tokens/month)", "AI / Cloud API", "Workbook assumption: 2 million tokens a month at 0.60 USD, for 10 months, at 280 PKR per USD. No separate actual was recorded.", "3360", "2026-08-12", "OpenAI"),
    ("text-embedding-3-small (M tokens/month)", "AI / Cloud API", "Workbook assumption: 5 million tokens a month at 0.02 USD, for 10 months, at 280 PKR per USD. No separate actual was recorded.", "280", "2026-08-12", "OpenAI"),
    ("Prepaid API credit buffer", "AI / Cloud API", "Workbook assumption: one 20 USD top-up at 280 PKR per USD. No separate actual was recorded.", "5600", "2026-08-12", "OpenAI"),
    ("Expo Push / FCM, Gmail SMTP", "AI / Cloud API", "Free notification tiers. Planned cost is zero.", 0, "2026-08-12", "Open-source / internal"),
    ("Developer laptops (16 GB RAM) - existing", "Hardware & Infrastructure", "Depreciation of 3 existing laptops at 250000 PKR over 36 months, for 10 project months. Not a new purchase. No separate actual was recorded.", "208333.33", "2026-04-15", "Estimated / To be confirmed"),
    ("On-premise server / workstation (32 GB RAM)", "Hardware & Infrastructure", "Depreciation of an existing server at 300000 PKR over 48 months, for 10 project months. No separate actual was recorded.", "62500", "2026-04-15", "Estimated / To be confirmed"),
    ("Android test phone (Android 10+)", "Hardware & Infrastructure", "Depreciation of one phone at 60000 PKR over 24 months, for 10 project months. No separate actual was recorded.", "25000", "2026-04-15", "Estimated / To be confirmed"),
    ("Internet (per member)", "Hardware & Infrastructure", "Assumption: 5000 PKR a month for each of 3 members, for 10 months. No separate actual was recorded.", "150000", "2026-04-15", "Estimated / To be confirmed"),
    ("Electricity for development (per member)", "Hardware & Infrastructure", "Assumption: 3000 PKR a month for each of 3 members, for 10 months. No separate actual was recorded.", "90000", "2026-04-15", "Estimated / To be confirmed"),
    ("External SSD 1 TB for backups", "Hardware & Infrastructure", "One-time backup drive at 18000 PKR, risk R10. No separate actual was recorded.", "18000", "2026-04-15", "Estimated / To be confirmed"),
    ("RAGAS evaluation API budget", "Testing", "One-time 15 USD evaluation budget at 280 PKR per USD. Testing starts 23 Dec 2026, after the status date, so no spend is recorded yet.", "4200", "2026-12-23", "Estimated / To be confirmed"),
    ("Locust load test & OWASP ZAP scan", "Testing", "Open-source test tools. Planned cost is zero.", 0, "2026-12-23", "Open-source / internal"),
    ("UAT sessions with NETS engineers (travel)", "Testing", "Assumption: 4 trips at 2000 PKR. UAT is scheduled for 20 Jan 2027, so no spend is recorded yet.", "8000", "2027-01-20", "Estimated / To be confirmed"),
    ("Requirement elicitation travel (NETS)", "Documentation & Handover", "Assumption: 3 trips at 2000 PKR during requirement elicitation. No separate actual was recorded.", "6000", "2026-04-22", "Estimated / To be confirmed"),
    ("Printing & binding (SRS + final report, 3 copies each)", "Documentation & Handover", "Assumption: 6 copies at 2500 PKR. Handover is scheduled for February 2027, so no spend is recorded yet.", "15000", "2027-02-03", "Estimated / To be confirmed"),
    ("Poster / demo-day material", "Documentation & Handover", "Assumption: 6000 PKR for the final demo. No spend is recorded yet.", "6000", "2027-02-09", "Estimated / To be confirmed"),
]


def main() -> None:
    rows = []
    variance_total = Decimal("0")
    estimated_total = Decimal("0")
    actual_total = Decimal("0")
    for name, wbs, finish, bac_raw, ac_raw, percent, resources, optimistic_days, likely_days, pessimistic_days, state in LABOUR:
        bac = money(bac_raw)
        workbook_actual = money(ac_raw)
        earned = money(bac * Decimal(str(percent)))
        optimistic, most_likely, pessimistic = pert_costs(bac, optimistic_days, likely_days, pessimistic_days)
        if state == "progress":
            remainder = money(bac - earned)
            rows.append(
                [
                    f"{name} (earned by 25 Oct 2026)",
                    "Personnel",
                    (
                        f"WBS {wbs}. Earned-value slice from the workbook status date 25 Oct 2026. "
                        f"Full task estimate {bac} PKR. Percent complete {percent}. "
                        f"Earned value {earned} PKR. Workbook actual cost {workbook_actual} PKR. "
                        f"Variance is workbook actual minus earned value."
                    ),
                    earned,
                    workbook_actual,
                    finish,
                    resources,
                    money(optimistic * earned / bac),
                    earned,
                    money(pessimistic * earned / bac),
                ]
            )
            rows.append(
                [
                    f"{name} (not yet earned)",
                    "Personnel",
                    (
                        f"WBS {wbs}. Remaining estimate after 25 Oct 2026. "
                        f"Workbook actual cost for this remainder is 0. "
                        f"Actual is set equal to the remaining estimate so unfinished work is not reported as a saving."
                    ),
                    remainder,
                    remainder,
                    finish,
                    resources,
                    money(optimistic - money(optimistic * earned / bac)),
                    remainder,
                    money(pessimistic - money(pessimistic * earned / bac)),
                ]
            )
        elif state == "future":
            rows.append(
                [
                    name,
                    "Personnel",
                    (
                        f"WBS {wbs}. Not started at the workbook status date 25 Oct 2026. "
                        f"Workbook actual cost is 0. Actual is set equal to the estimate so this future work is not reported as a saving."
                    ),
                    bac,
                    bac,
                    finish,
                    resources,
                    optimistic,
                    most_likely,
                    pessimistic,
                ]
            )
        else:
            rows.append(
                [
                    name,
                    "Personnel",
                    (
                        f"WBS {wbs}. Complete in the workbook earned-value sheet at 25 Oct 2026. "
                        f"Estimate {bac} PKR. Workbook actual cost {workbook_actual} PKR."
                    ),
                    bac,
                    workbook_actual,
                    finish,
                    resources,
                    optimistic,
                    most_likely,
                    pessimistic,
                ]
            )
    for name, category, description, amount, expense_date, vendor in NON_LABOUR:
        planned = money(amount)
        note = description + " Actual is set equal to the estimate, so this planned item does not create a negative variance."
        rows.append([name, category, note, planned, planned, expense_date, vendor, planned, planned, planned])

    for row in rows:
        estimated_total += row[3]
        actual_total += row[4]
        variance_total += row[4] - row[3]
        assert row[7] <= row[8] <= row[9], row[0]

    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
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
        )
        for row in rows:
            writer.writerow([row[0], row[1], row[2], f"{row[3]:f}", f"{row[4]:f}", row[5], row[6], f"{row[7]:f}", f"{row[8]:f}", f"{row[9]:f}"])
    print("rows", len(rows))
    print("estimated", estimated_total)
    print("actual", actual_total)
    print("variance", variance_total)


if __name__ == "__main__":
    main()
