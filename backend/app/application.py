from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import Settings
from app.db.session import create_db_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    engine = create_db_engine(config.resolved_database_path)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            # Fail visibly at startup if the configured SQLite file is unusable.
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="华园易享 API", version="0.6.0", lifespan=lifespan)
    application.state.settings = config
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    application.include_router(api_router)

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request, exception):
        # FastAPI's default errors echo input, including invalid plaintext passwords.
        details = [{key: error[key] for key in ("loc", "msg", "type")} for error in exception.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    @application.exception_handler(SQLAlchemyError)
    async def database_error(_request, _exception):
        # Never expose or log SQL parameter dumps (password/session hashes).
        return JSONResponse(status_code=503, content={"detail": "数据库暂不可用，请稍后重试。"})

    return application
