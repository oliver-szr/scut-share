from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Load process environment first, then backend/.env, then local defaults."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_path: Path = Path("data/scut_share.db")
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    app_env: Literal["development", "production"] = "development"
    session_ttl_seconds: int = Field(default=604800, ge=60, le=2592000)
    session_cookie_secure: bool = False
    session_cookie_name: str = Field(default="scut_share_session", pattern=r"^[A-Za-z0-9_]{1,64}$")
    upload_dir: Path = Path("data/uploads")
    max_image_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=20 * 1024 * 1024)

    @model_validator(mode="after")
    def validate_production_cookies(self):
        if self.app_env == "production":
            if not self.session_cookie_secure:
                raise ValueError("Production requires SESSION_COOKIE_SECURE=true and HTTPS")
            if any(urlsplit(origin).scheme != "https" for origin in self.cors_origins):
                raise ValueError("Production requires HTTPS frontend origins")
        return self

    @field_validator("cors_origins")
    @classmethod
    def validate_local_origins(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username is not None
                or parsed.password is not None
            ):
                raise ValueError("CORS_ORIGINS must contain explicit local origins without paths")
            # Validate the port as well as the origin structure.
            _ = parsed.port
        return origins

    @property
    def resolved_database_path(self) -> Path:
        path = self.database_path.expanduser()
        return (path if path.is_absolute() else BACKEND_ROOT / path).resolve()

    @property
    def resolved_upload_dir(self) -> Path:
        path = self.upload_dir.expanduser()
        return (path if path.is_absolute() else BACKEND_ROOT / path).resolve()
