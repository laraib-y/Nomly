import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.models import Base

MIGRATION = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0006_user_accounts.py"


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_0006", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(engine: sa.Engine, step) -> None:
    module = _load_migration()
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            getattr(module, step)()


def _pre_0006_schema(engine: sa.Engine) -> None:
    """Revision 0005 shape: everything except users, auth_sessions and sessions.user_id."""
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context) as op:
            with op.batch_alter_table("sessions", recreate="always") as batch:
                batch.drop_index("ix_sessions_user_id")
                batch.drop_column("user_id")
            op.drop_table("auth_sessions")
            op.drop_table("users")


def test_upgrade_keeps_existing_dinners_and_downgrade_is_clean() -> None:
    engine = sa.create_engine("sqlite://", poolclass=sa.pool.StaticPool)
    _pre_0006_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO sessions (id, room_code, description, status, created_at, updated_at) "
                "VALUES ('old-1', 'ABC123', 'Old guest dinner', 'completed', '2026-09-01', '2026-09-01')"
            )
        )

    _run(engine, "upgrade")
    _run(engine, "upgrade")
    inspector = sa.inspect(engine)
    assert {"users", "auth_sessions"} <= set(inspector.get_table_names())
    columns = {column["name"]: column for column in inspector.get_columns("sessions")}
    assert columns["user_id"]["nullable"] is True
    assert any(fk["referred_table"] == "users" for fk in inspector.get_foreign_keys("sessions"))
    with engine.connect() as connection:
        row = connection.execute(sa.text("SELECT room_code, user_id FROM sessions WHERE id = 'old-1'")).one()
    assert tuple(row) == ("ABC123", None)

    _run(engine, "downgrade")
    inspector = sa.inspect(engine)
    assert "users" not in inspector.get_table_names()
    assert "auth_sessions" not in inspector.get_table_names()
    assert "user_id" not in {column["name"] for column in inspector.get_columns("sessions")}
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT COUNT(*) FROM sessions")).scalar() == 1
