"""Database engine and session factory.

SQLite is the local default. Set DATABASE_URL to a PostgreSQL URL to switch engines
without changing the models.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import BACKEND_DIR, get_settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    if not url.startswith("sqlite:///"):
        return url
    path_part = url[len("sqlite:///") :]
    if path_part in {"", ":memory:"} or path_part.startswith("file:"):
        return url
    path = Path(path_part)
    if not path.is_absolute():
        path = (BACKEND_DIR / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return "sqlite:///" + path.as_posix()


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def make_engine(url: str | None = None):
    normalized = normalize_database_url(url or get_settings().database_url)
    return create_engine(normalized, **_engine_kwargs(normalized))


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    module_name = type(dbapi_connection).__module__
    if module_name.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def ensure_expense_pert_columns() -> None:
    """Add PERT columns to a database created before three-point estimates existed."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "expenses" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("expenses")}
    missing = [
        name
        for name in ("optimistic_cost", "most_likely_cost", "pessimistic_cost")
        if name not in existing
    ]
    if not missing:
        return
    with engine.begin() as connection:
        for name in missing:
            connection.execute(text(f"ALTER TABLE expenses ADD COLUMN {name} NUMERIC(14, 2)"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
