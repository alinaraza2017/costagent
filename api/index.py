"""Vercel serverless entry point for the CostWise AI API.

Vercel runs this file as a Python function. Every /api/* request is routed here
(see vercel.json) and handled by the same FastAPI app used locally.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base, engine, ensure_expense_pert_columns  # noqa: E402
from app.logging_config import logger  # noqa: E402
from app.main import app  # noqa: E402,F401  (Vercel looks for "app")


def _prepare_database() -> None:
    """Create tables and the fictional demo account on a cold start.

    Done here as well as in the FastAPI lifespan because a serverless platform
    may not send lifespan events. Both steps are safe to repeat.
    """
    try:
        Base.metadata.create_all(bind=engine)
        ensure_expense_pert_columns()
        from app.seed import seed

        seed()
    except Exception as exc:  # another cold start may be seeding at the same moment
        logger.warning("startup_prepare_skipped type=%s", type(exc).__name__)


_prepare_database()
