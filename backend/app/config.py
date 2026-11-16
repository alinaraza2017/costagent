"""Runtime configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
DEFAULT_DATABASE_PATH = BACKEND_DIR / "data" / "costwise.db"


class Settings(BaseSettings):
    app_name: str = "CostWise AI"
    secret_key: str = "replace-with-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    login_rate_limit: str = "5/minute"
    register_rate_limit: str = "10/minute"
    sensitive_rate_limit: str = "20/minute"
    max_upload_bytes: int = 5 * 1024 * 1024
    max_import_rows: int = 500
    max_json_bytes: int = 1 * 1024 * 1024
    bcrypt_rounds: int = 12
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 20
    debug: bool = False
    import_preview_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def ai_mode(self) -> str:
        return "external_llm" if self.llm_configured else "rule_based"


@lru_cache
def get_settings() -> Settings:
    return Settings()
