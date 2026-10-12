from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from app.core.config import BACKEND_ROOT
from app.db.session import Base, create_db_engine


def test_migration_initializes_fresh_database_and_matches_models(tmp_path):
    path = tmp_path / "migration.db"
    engine = create_db_engine(path)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
            assert set(inspect(connection).get_table_names()) == {"users", "auth_sessions", "items", "item_images", "trade_intents", "borrow_requests", "conversations", "messages", "reports", "report_appeals", "gift_requests", "alembic_version"}
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20261012_07"
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            connection.commit()
            command.upgrade(config, "head")  # Applying head twice does not recreate data.
            command.downgrade(config, "base")
            assert set(inspect(connection).get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_head_keeps_existing_user_data(tmp_path):
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    engine = create_db_engine(tmp_path / "upgrade.db")
    try:
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "20261012_02")
            connection.execute(text("INSERT INTO users (id, nickname, student_no, password_hash, campus) VALUES (1, '迁移测试', 'MIGRATION_A', 'test_hash', '五山校区')"))
            connection.execute(text("INSERT INTO items (id, owner_id, title, description, category, mode, campus, price_cents) VALUES (1, 1, '既有物品', '迁移保留', '其他', 'sale', '五山校区', 1200)"))
            connection.execute(text("INSERT INTO item_images (item_id, file_name, content_type) VALUES (1, 'existing.png', 'image/png')"))
            connection.commit()
            command.upgrade(config, "20261012_03")
            connection.execute(text("INSERT INTO users (id, nickname, student_no, password_hash, campus) VALUES (2, '买家同学', 'MIGRATION_B', 'test_hash', '五山校区')"))
            connection.execute(text("INSERT INTO trade_intents (item_id, buyer_id, seller_id, price_cents_snapshot) VALUES (1, 2, 1, 1200)"))
            connection.commit()
            command.upgrade(config, "20261012_04")
            connection.execute(text("INSERT INTO items (id, owner_id, title, description, category, mode, campus) VALUES (2, 1, '既有借还', '迁移保留', '其他', 'borrow', '五山校区')"))
            connection.execute(text("INSERT INTO borrow_requests (item_id, owner_id, borrower_id, requested_start_at, expected_return_at) VALUES (2, 1, 2, '2030-01-01', '2030-01-02')"))
            connection.commit()
            command.upgrade(config, "20261012_05")
            connection.execute(text("INSERT INTO conversations (id, context_type, item_id, participant_a_id, participant_b_id) VALUES (1, 'sale_item', 1, 1, 2)"))
            connection.execute(text("INSERT INTO messages (conversation_id, sender_id, content) VALUES (1, 2, '旧消息完整保留')"))
            connection.commit()
            command.upgrade(config, "head")
            assert connection.execute(text("SELECT student_no FROM users WHERE id=1")).scalar_one() == "MIGRATION_A"
            assert connection.execute(text("SELECT title, price_cents FROM items WHERE id=1")).one() == ("既有物品", 1200)
            assert connection.execute(text("SELECT file_name FROM item_images")).scalar_one() == "existing.png"
            assert connection.execute(text("SELECT status, price_cents_snapshot FROM trade_intents")).one() == ("pending", 1200)
            assert connection.execute(text("SELECT status FROM borrow_requests")).scalar_one() == "pending"
            assert connection.execute(text("SELECT content FROM messages")).scalar_one() == "旧消息完整保留"
            assert connection.execute(text("SELECT COUNT(*) FROM conversations")).scalar_one() == 1
            assert connection.execute(text("SELECT is_admin FROM users WHERE id=1")).scalar_one() == 0
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        engine.dispose()
