from alembic import context
from sqlalchemy import URL

from app.core.config import Settings
from app.db.session import Base, create_db_engine
from app.models.auth_session import AuthSession  # noqa: F401 -- register metadata
from app.models.user import User  # noqa: F401 -- register metadata
from app.models.item import Item, ItemImage  # noqa: F401 -- register metadata
from app.models.trade_intent import TradeIntent  # noqa: F401 -- register metadata
from app.models.borrow_request import BorrowRequest  # noqa: F401 -- register metadata
from app.models.conversation import Conversation, Message  # noqa: F401 -- register metadata
from app.models.report import Report, ReportAppeal  # noqa: F401 -- register metadata
from app.models.gift_request import GiftRequest  # noqa: F401 -- register metadata

config = context.config
target_metadata = Base.metadata


def run_with_connection(connection):
    driver = connection.connection.driver_connection
    cursor = driver.cursor()
    try:
        # SQLite batch rebuild must not cascade-delete children of items. This
        # setting applies only to the migration connection, never API sessions.
        cursor.execute("PRAGMA foreign_keys=OFF")
        if cursor.execute("PRAGMA foreign_keys").fetchone()[0] != 0:
            raise RuntimeError("SQLite 表迁移需要独立连接；请先提交既有事务并停止服务。")
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, transactional_ddl=True)
        with context.begin_transaction():
            if not driver.in_transaction:
                cursor.execute("BEGIN")
            context.run_migrations()
            if cursor.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("迁移后的外键完整性检查失败，迁移已中止。")
    finally:
        # Injected test connections can have an outer transaction. Their caller
        # commits it; pool checkout restores FK enforcement before any API use.
        if not driver.in_transaction:
            cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


if context.is_offline_mode():
    context.configure(
        url=URL.create("sqlite", database=str(Settings().resolved_database_path)),
        target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        run_with_connection(supplied_connection)
    else:
        engine = create_db_engine(Settings().resolved_database_path)
        try:
            with engine.connect() as connection:
                run_with_connection(connection)
        finally:
            engine.dispose()
