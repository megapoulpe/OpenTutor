"""Offline regression checks for the supported deployment configuration."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
from sqlalchemy.dialects import postgresql, sqlite

from config import Settings
from models.compat import CompatUUID, CompatJSONB


def test_postgres_url_uses_existing_async_sqlalchemy_driver():
    config = Settings(_env_file=None, database_url="postgresql://owner:fake@localhost/app")
    assert config.database_url == "postgresql+psycopg://owner:fake@localhost/app"


def test_supabase_transaction_pooler_requires_explicit_opt_in():
    with pytest.raises(ValueError, match="pool"):
        Settings(_env_file=None, database_url="postgresql://owner:fake@pool.supabase.com:6543/postgres")


def test_cloud_configuration_requires_private_storage_and_auth():
    with pytest.raises(ValueError, match="SUPABASE"):
        Settings(_env_file=None, auth_provider="supabase", auth_enabled=True)


def test_native_postgres_types_preserve_orm_contract():
    assert str(CompatUUID().compile(dialect=postgresql.dialect())) == "UUID"
    assert str(CompatJSONB().compile(dialect=postgresql.dialect())) == "JSONB"
    assert str(CompatUUID().compile(dialect=sqlite.dialect())) == "VARCHAR(36)"
