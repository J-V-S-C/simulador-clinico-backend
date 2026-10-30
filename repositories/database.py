"""Database mappings and transaction boundary."""

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)


class TokenRow(Base):
    __tablename__ = "tokens"
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AdminTokenRow(Base):
    __tablename__ = "admin_tokens"
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CaseRow(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)


class SimulationRow(Base):
    __tablename__ = "simulations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    payload: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    clock_checkpoint: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReportRow(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    simulation_id: Mapped[str] = mapped_column(ForeignKey("simulations.id"), index=True)
    interaction_id: Mapped[str] = mapped_column(String(36))
    description: Mapped[str] = mapped_column(String(2000))
    response: Mapped[str] = mapped_column(String(4000))
    context: Mapped[str] = mapped_column(String(4000))


class ExperienceFeedbackRow(Base):
    __tablename__ = "experience_feedback"
    simulation_id: Mapped[str] = mapped_column(ForeignKey("simulations.id"), primary_key=True)
    liked: Mapped[bool] = mapped_column(Boolean)
    clarity: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(Integer)
    useful_feature: Mapped[str] = mapped_column(String(1000), default="")
    improvement: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def run_migrations(database_url: str) -> None:
    """Upgrade a new database; recognize the prototype schema created before Alembic."""
    from alembic import command
    from alembic.config import Config

    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    if {"users", "cases", "simulations", "tokens", "reports"} <= tables and "alembic_version" not in tables:
        with engine.connect() as connection:
            user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        revision = ("d9b31a4f5e67" if "name" in user_columns else
                    "c8a12f9e2d34" if "experience_feedback" in tables else "b6dd5a8bb57b")
        command.stamp(config, revision)
        command.upgrade(config, "head")
    else:
        command.upgrade(config, "head")
    engine.dispose()


def create_session_factory(database_url: str, create_schema: bool = True) -> sessionmaker[Session]:
    if database_url.startswith("sqlite:///") and ":memory:" not in database_url:
        Path(database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {})
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def sqlite_pragmas(connection, _):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()
        if ":memory:" not in database_url:
            with engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL")
    if create_schema:
        Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
