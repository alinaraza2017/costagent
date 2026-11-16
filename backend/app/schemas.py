"""Request and response schemas."""

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants import CATEGORIES, CURRENCIES, PROJECT_STATUSES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address")
    return email


def clean_text(value: str, *, max_length: int, field_name: str, required: bool = True) -> str:
    text = "" if value is None else str(value).strip()
    if any(ord(character) < 32 for character in text):
        raise ValueError(f"{field_name} contains unsupported characters")
    if not text.isprintable():
        raise ValueError(f"{field_name} contains unsupported characters")
    if required and not text:
        raise ValueError(f"{field_name} is required")
    if len(text) > max_length:
        raise ValueError(f"{field_name} must be {max_length} characters or fewer")
    return text


def validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 bytes or fewer")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must include a letter and a number")
    return value


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value, max_length=120, field_name="Full name")

    @field_validator("password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserPublic(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime
    ai_mode: str


class ProfileUpdate(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value, max_length=120, field_name="Full name")


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, value: str) -> str:
        return validate_password(value)


class ProjectInput(BaseModel):
    name: str
    description: str = ""
    start_date: date
    end_date: date | None = None
    budget: float = Field(ge=0, le=100_000_000_000)
    currency: str = "PKR"
    status: str = "planning"

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value, max_length=200, field_name="Project name")

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return clean_text(value, max_length=2000, field_name="Description", required=False)

    @field_validator("currency")
    @classmethod
    def _currency(cls, value: str) -> str:
        code = value.strip().upper()
        if code not in CURRENCIES:
            raise ValueError("Select a supported currency")
        return code

    @field_validator("status")
    @classmethod
    def _status(cls, value: str) -> str:
        if value not in PROJECT_STATUSES:
            raise ValueError("Select a supported project status")
        return value

    @field_validator("end_date")
    @classmethod
    def _end_date(cls, value: date | None, info):
        start = info.data.get("start_date")
        if value is not None and start is not None and value < start:
            raise ValueError("End date cannot be earlier than the start date")
        return value


class ExpenseInput(BaseModel):
    expense_name: str
    category: str
    description: str = ""
    estimated_cost: float = Field(ge=0, le=100_000_000_000)
    actual_cost: float = Field(ge=0, le=100_000_000_000)
    optimistic_cost: float | None = Field(default=None, ge=0, le=100_000_000_000)
    most_likely_cost: float | None = Field(default=None, ge=0, le=100_000_000_000)
    pessimistic_cost: float | None = Field(default=None, ge=0, le=100_000_000_000)
    expense_date: date
    vendor: str | None = None

    @field_validator("expense_name")
    @classmethod
    def _name(cls, value: str) -> str:
        return clean_text(value, max_length=200, field_name="Expense name")

    @field_validator("category")
    @classmethod
    def _category(cls, value: str) -> str:
        cleaned = value.strip().lower()
        for category in CATEGORIES:
            if category.lower() == cleaned:
                return category
        raise ValueError("Select a supported category")

    @field_validator("description")
    @classmethod
    def _description(cls, value: str) -> str:
        return clean_text(value, max_length=2000, field_name="Description", required=False)

    @field_validator("vendor")
    @classmethod
    def _vendor(cls, value: str | None) -> str | None:
        if value is None or not str(value).strip():
            return None
        return clean_text(value, max_length=200, field_name="Vendor")

    @model_validator(mode="after")
    def _pert_points(self):
        points = (self.optimistic_cost, self.most_likely_cost, self.pessimistic_cost)
        if all(point is None for point in points):
            return self
        if any(point is None for point in points):
            raise ValueError("Enter optimistic, most likely, and pessimistic costs together, or leave all three blank")
        if not (self.optimistic_cost <= self.most_likely_cost <= self.pessimistic_cost):
            raise ValueError("Optimistic cost cannot exceed the most likely cost, and the most likely cost cannot exceed the pessimistic cost")
        return self


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    expense_name: str
    category: str
    description: str
    estimated_cost: float
    actual_cost: float
    optimistic_cost: float | None = None
    most_likely_cost: float | None = None
    pessimistic_cost: float | None = None
    pert_expected: float | None = None
    pert_std_dev: float | None = None
    variance: float
    percentage_variance: float | None
    variance_interpretation: str
    expense_date: date
    vendor: str | None
    created_at: datetime
    updated_at: datetime


class SummaryOut(BaseModel):
    total_estimated: float
    total_actual: float
    total_variance: float
    percentage_variance: float | None
    expense_count: int
    over_budget_count: int
    under_budget_count: int
    on_budget_count: int
    interpretation: str
    currency: str
    mixed_currencies: bool = False
    currencies_present: list[str] = []


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str
    start_date: date
    end_date: date | None
    budget: float
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    summary: SummaryOut


class PageOut(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    total: int
    page: int
    page_size: int


class ExpensePage(BaseModel):
    items: list[ExpenseOut]
    total: int
    page: int
    page_size: int


class RowIssue(BaseModel):
    row_number: int
    field: str | None = None
    message: str


class ExpensePreview(BaseModel):
    source_row: int
    expense_name: str
    category: str
    description: str
    estimated_cost: float
    actual_cost: float
    variance: float
    percentage_variance: float | None
    expense_date: date
    vendor: str | None


class ImportPreviewOut(BaseModel):
    import_id: int | None
    needs_mapping: bool
    detected_columns: list[str]
    missing_fields: list[str]
    suggested_mapping: dict[str, str]
    valid_rows: list[ExpensePreview]
    errors: list[RowIssue]
    duplicates: list[RowIssue]
    duplicate_policy: str
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    message: str


class ImportConfirmIn(BaseModel):
    import_id: int


class ImportSummaryOut(BaseModel):
    import_id: int
    status: str
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    imported_count: int
    message: str


class ChartPoint(BaseModel):
    label: str
    estimated: float
    actual: float
    variance: float


class TimePoint(BaseModel):
    label: str
    estimated: float
    actual: float
    cumulative_actual: float


class CategorySlice(BaseModel):
    label: str
    actual: float


class ChartsOut(BaseModel):
    by_category: list[ChartPoint]
    by_project: list[ChartPoint]
    variance_by_category: list[ChartPoint]
    spending_over_time: list[TimePoint]
    category_distribution: list[CategorySlice]
    currency: str


class OverBudgetItem(BaseModel):
    expense_name: str
    category: str
    estimated_cost: float
    actual_cost: float
    variance: float
    percentage_variance: float | None


class AnomalyItem(BaseModel):
    expense_name: str
    category: str
    actual_cost: float
    peer_count: int
    upper_fence: float
    reason: str


class CategorySpend(BaseModel):
    category: str
    actual_cost: float
    estimated_cost: float
    variance: float


class SampleNote(BaseModel):
    category: str
    peer_count: int
    message: str


class NarrativeOut(BaseModel):
    summary: str
    hypotheses: list[str]
    recommendations: list[str]
    budget_health: Literal["within_budget", "watch", "over_budget", "no_data"]
    budget_health_label: str


class AnalysisOut(BaseModel):
    project_id: int
    project_name: str
    currency: str
    mode: Literal["rule_based", "external_llm"]
    mode_label: str
    fallback_reason: str | None = None
    summary_metrics: SummaryOut
    highest_spending_categories: list[CategorySpend]
    over_budget_expenses: list[OverBudgetItem]
    anomalies: list[AnomalyItem]
    insufficient_sample: list[SampleNote]
    hypotheses: list[str]
    recommendations: list[str]
    budget_health: str
    budget_health_label: str
    summary: str
    disclaimer: str


class ThreatOut(BaseModel):
    id: str
    name: str
    scenario: str
    impact: str
    mitigation: str
    status: str
    test_case: str
    future_improvement: str


class ChecklistItemOut(BaseModel):
    key: str
    title: str
    guidance: str
    completed: bool
    updated_at: datetime | None = None


class ChecklistUpdate(BaseModel):
    completed: bool


class AuditLogOut(BaseModel):
    id: int
    event_type: str
    detail: str
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


class MessageOut(BaseModel):
    message: str


class PertActivity(BaseModel):
    expense_id: int
    expense_name: str
    category: str
    optimistic_cost: float
    most_likely_cost: float
    pessimistic_cost: float
    expected_cost: float
    std_dev: float
    variance: float


class PertMissing(BaseModel):
    expense_id: int
    expense_name: str
    estimated_cost: float


class PertRange(BaseModel):
    label: str
    low: float
    high: float


class PertOut(BaseModel):
    project_id: int
    project_name: str
    currency: str
    budget: float
    activity_count: int
    missing_count: int
    expected_cost: float | None
    std_dev: float | None
    variance: float | None
    budget_probability: float | None
    ranges: list[PertRange]
    activities: list[PertActivity]
    missing: list[PertMissing]
    assumption: str
    suggest_note: str
    suggested_count: int = 0


class CompareCategory(BaseModel):
    category: str
    estimated: float
    actual: float


class CompareSide(BaseModel):
    id: int
    name: str
    status: str
    currency: str
    start_date: date
    end_date: date | None
    budget: float
    expense_count: int
    total_estimated: float
    total_actual: float
    total_variance: float
    percentage_variance: float | None
    pert_expected: float | None
    pert_std_dev: float | None
    pert_activity_count: int
    pert_missing_count: int
    categories: list[CompareCategory]


class CompareDeltas(BaseModel):
    budget: float
    total_estimated: float
    total_actual: float
    total_variance: float
    pert_expected: float | None


class CompareCategoryRow(BaseModel):
    category: str
    left_estimated: float
    left_actual: float
    right_estimated: float
    right_actual: float


class CompareOut(BaseModel):
    same_currency: bool
    left: CompareSide
    right: CompareSide
    deltas: CompareDeltas | None
    category_rows: list[CompareCategoryRow]
    notes: list[str]
