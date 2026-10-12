import pytest
from fastapi.testclient import TestClient

from app.application import create_app
from app.core.config import Settings
from alembic import command
from alembic.config import Config
from app.core.config import BACKEND_ROOT


@pytest.fixture
def test_app(tmp_path):
    # Import the factory, not app.main: never initialize the development database.
    settings = Settings(
        _env_file=None,
        database_path=tmp_path / "test.db",
        upload_dir=tmp_path / "uploads",
        cors_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        app_env="development", session_cookie_secure=False, session_ttl_seconds=3600,
    )
    application = create_app(settings)
    migration_config = Config(str(BACKEND_ROOT / "alembic.ini"))
    with application.state.engine.begin() as connection:
        migration_config.attributes["connection"] = connection
        command.upgrade(migration_config, "head")
    yield application
    application.state.engine.dispose()


@pytest.fixture
def client(test_app):
    with TestClient(test_app) as test_client:
        yield test_client
