from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.config import get_settings


def test_migrations_upgrade_and_downgrade(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config("alembic.ini")

    try:
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        inspector = inspect(engine)

        assert "patients" in inspector.get_table_names()
        assert {"last_name", "date_of_birth", "phone_number"} <= {
            column
            for index in inspector.get_indexes("patients")
            for column in index["column_names"]
        }

        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() == "20260901_01"
        command.downgrade(config, "base")
        assert "patients" not in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        get_settings.cache_clear()
