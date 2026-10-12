from sqlalchemy import text


def test_sqlite_connection_uses_temporary_file(test_app, tmp_path):
    engine = test_app.state.engine
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
    assert engine.url.database == str(tmp_path / "test.db")
    assert (tmp_path / "test.db").is_file()


def test_session_transaction_is_persisted_only_in_temporary_database(test_app):
    factory = test_app.state.session_factory
    with factory() as session:
        session.execute(text("CREATE TABLE test_probe (value INTEGER NOT NULL)"))
        session.execute(text("INSERT INTO test_probe (value) VALUES (42)"))
        session.commit()
    with factory() as session:
        assert session.execute(text("SELECT value FROM test_probe")).scalar_one() == 42
        session.execute(text("INSERT INTO test_probe (value) VALUES (99)"))
        session.rollback()
        assert session.execute(text("SELECT COUNT(*) FROM test_probe")).scalar_one() == 1
