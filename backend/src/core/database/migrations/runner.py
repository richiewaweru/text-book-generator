from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from core.config import settings


def _alembic_config() -> Config:
    config_path = Path(__file__).resolve().parents[4] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def upgrade_database(revision: str = "head") -> None:
    command.upgrade(_alembic_config(), revision)
