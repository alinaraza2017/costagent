"""Two-stage CSV and XLSX import.

Files are parsed as data. Spreadsheet formulas are not evaluated.
"""

import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from fastapi import HTTPException
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants import CATEGORIES, DUPLICATE_POLICY
from app.models import Expense, ImportSession, Project
from app.schemas import clean_text
from app.services.calculations import as_float, money, percentage_variance, variance

REQUIRED_FIELDS = ["expense_name", "category", "estimated_cost", "actual_cost", "expense_date"]
OPTIONAL_FIELDS = ["description", "vendor", "optimistic_cost", "most_likely_cost", "pessimistic_cost"]
ALIASES = {
    "expense_name": ["expense_name", "expense", "name", "expense_title"],
    "category": ["category", "cost_category"],
    "estimated_cost": ["estimated_cost", "estimated", "estimate", "budgeted_cost"],
    "actual_cost": ["actual_cost", "actual", "spent"],
    "expense_date": ["expense_date", "date", "spent_on"],
    "description": ["description", "details", "notes"],
    "vendor": ["vendor", "supplier"],
    "optimistic_cost": ["optimistic_cost", "optimistic", "pert_optimistic"],
    "most_likely_cost": ["most_likely_cost", "most_likely", "pert_most_likely"],
    "pessimistic_cost": ["pessimistic_cost", "pessimistic", "pert_pessimistic"],
}


class ImportRejected(Exception):
    def __init__(self, message: str):
        self.message = message


def sample_template_csv() -> str:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[1] / "resources" / "cost_import_template.csv",
        here.parents[3] / "samples" / "cost_import_template.csv",
        here.parents[2] / "samples" / "cost_import_template.csv",
    ]
    for template in candidates:
        if template.exists():
            return template.read_text(encoding="utf-8")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(REQUIRED_FIELDS + OPTIONAL_FIELDS)
    return buffer.getvalue()


def _normalize_header(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def suggest_mapping(columns: list[str]) -> dict[str, str]:
    lookup = {_normalize_header(column): column for column in columns if str(column).strip()}
    mapping: dict[str, str] = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if alias in lookup:
                mapping[field] = lookup[alias]
                break
    return mapping


def parse_cost(value, *, blank_as_zero: bool = False) -> Decimal:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if blank_as_zero:
            return Decimal("0.00")
        raise ValueError("Cost is required")
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text == "":
            if blank_as_zero:
                return Decimal("0.00")
            raise ValueError("Cost is required")
        if text[0] in {"=", "+", "@"}:
            raise ValueError("Formulas are not accepted. Enter a plain number.")
        if any(character in text for character in "()"):
            raise ValueError("Enter a plain number without formulas.")
        raw = text
    else:
        raw = str(value).strip()
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        raise ValueError("Enter a valid cost") from None
    if amount < 0:
        raise ValueError("Cost cannot be negative")
    if amount > Decimal("100000000000"):
        raise ValueError("Cost is too large")
    return money(amount)


def parse_import_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        raise ValueError("Expense date is required")
    text = str(value).strip()
    if not text:
        raise ValueError("Expense date is required")
    if " " in text:
        text = text.split(" ")[0]
    if "T" in text:
        text = text.split("T")[0]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            break
        except ValueError:
            parsed = None
    if parsed is None:
        raise ValueError("Use the date format YYYY-MM-DD")
    if parsed.year < 1990 or parsed.year > 2100:
        raise ValueError("Expense date is outside the supported range")
    return parsed


def canonical_category(value) -> str:
    if value is None or not str(value).strip():
        raise ValueError("Category is required")
    cleaned = str(value).strip().lower()
    for category in CATEGORIES:
        if category.lower() == cleaned:
            return category
    raise ValueError("Category is not supported")


def load_table(filename: str, content: bytes) -> pd.DataFrame:
    settings = get_settings()
    if not filename or "." not in filename:
        raise ImportRejected("Upload a .csv or .xlsx file.")
    extension = "." + filename.rsplit(".", 1)[-1].lower()
    if extension not in {".csv", ".xlsx"}:
        raise ImportRejected("Unsupported file type. Upload a .csv or .xlsx file.")
    if not content:
        raise ImportRejected("The file is empty.")
    if len(content) > settings.max_upload_bytes:
        raise ImportRejected("The file exceeds the 5 MB size limit.")
    if extension == ".csv":
        return _load_csv(content)
    return _load_xlsx(content)


def _load_csv(content: bytes) -> pd.DataFrame:
    if content.startswith(b"PK"):
        raise ImportRejected("The file content does not match a CSV file.")
    if b"\x00" in content:
        raise ImportRejected("The file content is not valid CSV text.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("cp1252")
        except UnicodeDecodeError:
            raise ImportRejected("Save the CSV file as UTF-8 and try again.") from None
    try:
        frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    except pd.errors.ParserError:
        raise ImportRejected("The CSV file could not be parsed. Check that it uses commas and a header row.") from None
    except Exception:
        raise ImportRejected("The CSV file could not be parsed.") from None
    return frame


def _load_xlsx(content: bytes) -> pd.DataFrame:
    if not content.startswith(b"PK\x03\x04"):
        raise ImportRejected("The file content does not match an Excel .xlsx workbook.")
    if b"vbaProject.bin" in content:
        raise ImportRejected("Macro-enabled workbooks are not accepted.")
    try:
        workbook = load_workbook(io.BytesIO(content), data_only=False, read_only=True, keep_links=False)
    except Exception:
        raise ImportRejected("The Excel file could not be parsed.") from None
    try:
        worksheet = workbook.active
        if worksheet is None:
            raise ImportRejected("The workbook has no worksheet.")
        rows = []
        formula_rows = []
        for row_index, row in enumerate(worksheet.iter_rows(), start=1):
            values = []
            for cell in row:
                if cell.data_type == "f":
                    formula_rows.append(row_index)
                    values.append(None)
                else:
                    values.append(cell.value)
            rows.append(values)
    finally:
        workbook.close()
    if not rows:
        raise ImportRejected("The spreadsheet is empty.")
    header = ["" if cell is None else str(cell).strip() for cell in rows[0]]
    frame = pd.DataFrame(rows[1:], columns=header)
    frame.attrs["formula_rows"] = formula_rows
    return frame


def _resolve_mapping(columns: list[str], column_map: dict[str, str] | None) -> tuple[dict[str, str], list[str]]:
    suggested = suggest_mapping(columns)
    resolved = dict(suggested)
    if column_map:
        for field, header in column_map.items():
            if field in REQUIRED_FIELDS + OPTIONAL_FIELDS and header in columns:
                resolved[field] = header
    missing = [field for field in REQUIRED_FIELDS if field not in resolved]
    return resolved, missing


def _cell(row, header: str | None):
    if header is None or header not in row.index:
        return None
    value = row[header]
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    return value


def _duplicate_key(name: str, category: str, expense_date: date, estimated: Decimal, actual: Decimal) -> tuple:
    return (name.strip().lower(), category, expense_date.isoformat(), str(estimated), str(actual))


def build_preview(
    db: Session,
    project: Project,
    user_id: int,
    filename: str,
    content: bytes,
    column_map: dict[str, str] | None,
) -> dict:
    settings = get_settings()
    frame = load_table(filename, content)
    columns = [str(column) for column in frame.columns]
    if len(columns) > 50:
        raise ImportRejected("The file has too many columns.")
    if any(not str(column).strip() for column in columns):
        raise ImportRejected("Every column needs a header.")
    resolved, missing = _resolve_mapping(columns, column_map)
    detected = columns
    if missing:
        return {
            "import_id": None,
            "needs_mapping": True,
            "detected_columns": detected,
            "missing_fields": missing,
            "suggested_mapping": suggest_mapping(columns),
            "valid_rows": [],
            "errors": [],
            "duplicates": [],
            "duplicate_policy": DUPLICATE_POLICY,
            "accepted_count": 0,
            "rejected_count": 0,
            "duplicate_count": 0,
            "message": "Map the missing columns, then preview the file again. Nothing has been saved.",
        }

    data_rows = frame.dropna(how="all")
    if len(data_rows.index) > settings.max_import_rows:
        raise ImportRejected(f"The file exceeds the limit of {settings.max_import_rows} data rows.")
    if data_rows.empty:
        raise ImportRejected("The file has no data rows.")

    existing = {
        _duplicate_key(
            item.expense_name,
            item.category,
            item.expense_date,
            money(item.estimated_cost),
            money(item.actual_cost),
        )
        for item in db.query(Expense).filter(Expense.project_id == project.id).all()
    }
    seen: set[tuple] = set()
    valid_rows = []
    errors = []
    duplicates = []
    formula_rows = set(frame.attrs.get("formula_rows", []))
    blank_actuals = 0

    for index, row in data_rows.iterrows():
        row_number = int(index) + 2
        if row_number in formula_rows:
            errors.append(
                {
                    "row_number": row_number,
                    "field": None,
                    "message": "Spreadsheet formulas are not accepted. Enter plain values.",
                }
            )
            continue
        try:
            parsed, actual_was_blank = _parse_row(row, resolved)
        except ValueError as exc:
            errors.append({"row_number": row_number, "field": None, "message": str(exc)})
            continue
        key = _duplicate_key(
            parsed["expense_name"],
            parsed["category"],
            parsed["expense_date"],
            parsed["estimated_cost"],
            parsed["actual_cost"],
        )
        if key in seen or key in existing:
            duplicates.append(
                {
                    "row_number": row_number,
                    "field": "expense_name",
                    "message": "Duplicate row skipped. It matches another row in this file or an expense already saved on the project.",
                }
            )
            continue
        if actual_was_blank:
            blank_actuals += 1
        seen.add(key)
        valid_rows.append({"source_row": row_number, **_serialize_row(parsed)})

    payload = {"valid_rows": valid_rows, "errors": errors, "duplicates": duplicates}
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.import_preview_minutes)
    session = ImportSession(
        project_id=project.id,
        user_id=user_id,
        filename=Path(filename).name[-255:],
        status="preview",
        payload_json=json.dumps(payload),
        accepted_count=len(valid_rows),
        rejected_count=len(errors),
        duplicate_count=len(duplicates),
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    message = "Review the preview. Valid rows are saved only after you confirm."
    if blank_actuals:
        message += f" {blank_actuals} rows had no actual cost, so actual cost was set to 0."
    if not valid_rows:
        message = "No valid rows were found. Nothing will be saved until a preview contains valid rows and you confirm it."
    return _preview_response(session, payload, detected, resolved, message)


def _parse_row(row, mapping: dict[str, str]) -> tuple[dict, bool]:
    name = clean_text(str(_cell(row, mapping["expense_name"]) or ""), max_length=200, field_name="Expense name")
    category = canonical_category(_cell(row, mapping["category"]))
    estimated = parse_cost(_cell(row, mapping["estimated_cost"]))
    actual_raw = _cell(row, mapping["actual_cost"])
    actual_was_blank = actual_raw is None or str(actual_raw).strip() == ""
    actual = parse_cost(actual_raw, blank_as_zero=True)
    expense_date = parse_import_date(_cell(row, mapping["expense_date"]))
    description_header = mapping.get("description")
    vendor_header = mapping.get("vendor")
    description = clean_text(
        str(_cell(row, description_header) or ""),
        max_length=2000,
        field_name="Description",
        required=False,
    )
    vendor_raw = _cell(row, vendor_header)
    vendor = None
    if vendor_raw is not None and str(vendor_raw).strip():
        vendor = clean_text(str(vendor_raw), max_length=200, field_name="Vendor")
    optimistic, most_likely, pessimistic = _parse_pert(row, mapping)
    return {
        "expense_name": name,
        "category": category,
        "description": description,
        "estimated_cost": estimated,
        "actual_cost": actual,
        "expense_date": expense_date,
        "vendor": vendor,
        "optimistic_cost": optimistic,
        "most_likely_cost": most_likely,
        "pessimistic_cost": pessimistic,
    }, actual_was_blank


def _blank_cell(value) -> bool:
    return value is None or str(value).strip() == ""


def _parse_pert(row, mapping: dict[str, str]) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    parsed: list[Decimal | None] = []
    for field in ("optimistic_cost", "most_likely_cost", "pessimistic_cost"):
        header = mapping.get(field)
        raw = _cell(row, header) if header else None
        parsed.append(None if _blank_cell(raw) else parse_cost(raw))
    if all(point is None for point in parsed):
        return None, None, None
    if any(point is None for point in parsed):
        raise ValueError("Enter optimistic, most likely, and pessimistic costs together, or leave all three blank")
    optimistic, most_likely, pessimistic = parsed
    if not (optimistic <= most_likely <= pessimistic):
        raise ValueError("Optimistic cost cannot exceed the most likely cost, and the most likely cost cannot exceed the pessimistic cost")
    return optimistic, most_likely, pessimistic


def _serialize_row(parsed: dict) -> dict:
    return {
        "expense_name": parsed["expense_name"],
        "category": parsed["category"],
        "description": parsed["description"],
        "estimated_cost": str(parsed["estimated_cost"]),
        "actual_cost": str(parsed["actual_cost"]),
        "expense_date": parsed["expense_date"].isoformat(),
        "vendor": parsed["vendor"],
        "optimistic_cost": None if parsed.get("optimistic_cost") is None else str(parsed["optimistic_cost"]),
        "most_likely_cost": None if parsed.get("most_likely_cost") is None else str(parsed["most_likely_cost"]),
        "pessimistic_cost": None if parsed.get("pessimistic_cost") is None else str(parsed["pessimistic_cost"]),
    }


def _preview_row(raw: dict) -> dict:
    estimated = Decimal(raw["estimated_cost"])
    actual = Decimal(raw["actual_cost"])
    percent = percentage_variance(actual, estimated)
    return {
        "source_row": raw["source_row"],
        "expense_name": raw["expense_name"],
        "category": raw["category"],
        "description": raw["description"],
        "estimated_cost": as_float(estimated),
        "actual_cost": as_float(actual),
        "variance": as_float(variance(actual, estimated)),
        "percentage_variance": as_float(percent) if percent is not None else None,
        "expense_date": date.fromisoformat(raw["expense_date"]),
        "vendor": raw.get("vendor"),
    }


def _preview_response(session: ImportSession, payload: dict, columns: list[str], mapping: dict[str, str], message: str) -> dict:
    return {
        "import_id": session.id,
        "needs_mapping": False,
        "detected_columns": columns,
        "missing_fields": [],
        "suggested_mapping": {field: header for field, header in mapping.items() if field in REQUIRED_FIELDS + OPTIONAL_FIELDS},
        "valid_rows": [_preview_row(row) for row in payload["valid_rows"]],
        "errors": payload["errors"],
        "duplicates": payload["duplicates"],
        "duplicate_policy": DUPLICATE_POLICY,
        "accepted_count": session.accepted_count,
        "rejected_count": session.rejected_count,
        "duplicate_count": session.duplicate_count,
        "message": message,
    }


def confirm_import(db: Session, session: ImportSession) -> ImportSession:
    if session.status == "confirmed":
        raise HTTPException(status_code=409, detail="This import was already confirmed.")
    if session.status == "cancelled":
        raise HTTPException(status_code=409, detail="This import was cancelled. Upload the file again to create a new preview.")
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This preview has expired. Upload the file again.")
    payload = json.loads(session.payload_json or "{}")
    raw_rows = payload.get("valid_rows") or []
    if not raw_rows:
        raise HTTPException(status_code=400, detail="There are no valid rows to import.")

    try:
        existing = {
            _duplicate_key(
                item.expense_name,
                item.category,
                item.expense_date,
                money(item.estimated_cost),
                money(item.actual_cost),
            )
            for item in db.query(Expense).filter(Expense.project_id == session.project_id).all()
        }
        created = 0
        for raw in raw_rows:
            parsed = _revalidate(raw)
            key = _duplicate_key(
                parsed["expense_name"],
                parsed["category"],
                parsed["expense_date"],
                parsed["estimated_cost"],
                parsed["actual_cost"],
            )
            if key in existing:
                continue
            existing.add(key)
            db.add(
                Expense(
                    project_id=session.project_id,
                    expense_name=parsed["expense_name"],
                    category=parsed["category"],
                    description=parsed["description"],
                    estimated_cost=parsed["estimated_cost"],
                    actual_cost=parsed["actual_cost"],
                    expense_date=parsed["expense_date"],
                    vendor=parsed["vendor"],
                    optimistic_cost=parsed["optimistic_cost"],
                    most_likely_cost=parsed["most_likely_cost"],
                    pessimistic_cost=parsed["pessimistic_cost"],
                )
            )
            created += 1
        session.status = "confirmed"
        session.imported_count = created
        db.commit()
        db.refresh(session)
        return session
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="The import could not be saved. No records were written.") from None


def _revalidate(raw: dict) -> dict:
    try:
        name = clean_text(raw["expense_name"], max_length=200, field_name="Expense name")
        category = canonical_category(raw["category"])
        estimated = parse_cost(raw["estimated_cost"])
        actual = parse_cost(raw["actual_cost"])
        expense_date = parse_import_date(raw["expense_date"])
        description = clean_text(raw.get("description") or "", max_length=2000, field_name="Description", required=False)
        vendor = raw.get("vendor")
        if vendor:
            vendor = clean_text(str(vendor), max_length=200, field_name="Vendor")
        else:
            vendor = None
        pert = []
        for key in ("optimistic_cost", "most_likely_cost", "pessimistic_cost"):
            value = raw.get(key)
            pert.append(None if value is None or value == "" else parse_cost(value))
        if any(point is not None for point in pert) and any(point is None for point in pert):
            raise ValueError("PERT costs must be complete")
        if all(point is not None for point in pert) and not (pert[0] <= pert[1] <= pert[2]):
            raise ValueError("PERT costs are out of order")
    except (KeyError, ValueError, InvalidOperation):
        raise HTTPException(status_code=400, detail="The preview could not be confirmed because a row is no longer valid. No records were written.") from None
    return {
        "expense_name": name,
        "category": category,
        "description": description,
        "estimated_cost": estimated,
        "actual_cost": actual,
        "expense_date": expense_date,
        "vendor": vendor,
        "optimistic_cost": pert[0],
        "most_likely_cost": pert[1],
        "pessimistic_cost": pert[2],
    }


def cancel_import(db: Session, session: ImportSession) -> ImportSession:
    if session.status == "confirmed":
        raise HTTPException(status_code=409, detail="This import was already confirmed and cannot be cancelled.")
    session.status = "cancelled"
    db.commit()
    db.refresh(session)
    return session


def summary_message(session: ImportSession) -> str:
    if session.status == "preview":
        return "Preview only. Records are not saved until you confirm."
    if session.status == "cancelled":
        return "Import cancelled. No records from this preview were saved."
    return f"Import confirmed. {session.imported_count} records were saved."
