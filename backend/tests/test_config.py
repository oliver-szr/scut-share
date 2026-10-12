from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_ROOT, Settings


def test_relative_database_path_is_based_on_backend_root():
    config = Settings(_env_file=None, database_path=Path("data/example.db"))
    assert config.resolved_database_path == (BACKEND_ROOT / "data/example.db").resolve()


@pytest.mark.parametrize("origin", ["*", "https://example.com", "http://localhost:5173/path"])
def test_config_rejects_nonlocal_or_wildcard_cors(origin):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, cors_origins=[origin])


def test_production_requires_secure_cookies_and_https_origins():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", session_cookie_secure=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production", session_cookie_secure=True, cors_origins=["http://localhost:5173"])
    config = Settings(_env_file=None, app_env="production", session_cookie_secure=True, cors_origins=["https://localhost:5173"])
    assert config.session_cookie_secure
