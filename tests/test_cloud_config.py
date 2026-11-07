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


def test_supabase_transaction_pooler_is_not_a_supported_deployment_mode():
    with pytest.raises(ValueError, match="pool"):
        Settings(_env_file=None, database_url="postgresql://owner:fake@pool.supabase.com:6543/postgres")


def test_remote_postgres_always_verifies_server_with_automatic_ca():
    from pathlib import Path
    config = Settings(_env_file=None, database_url="postgresql://owner:fake@pool.supabase.com:5432/postgres?sslmode=disable")
    assert config.postgres_connect_args["sslmode"] == "verify-full"
    assert Path(config.postgres_connect_args["sslrootcert"]).is_file()


def test_local_postgres_does_not_require_a_tls_server():
    config = Settings(_env_file=None, database_url="postgresql://owner:fake@127.0.0.1:55432/app")
    assert config.postgres_connect_args == {"sslmode": "disable"}


def test_production_defaults_need_only_credentials_and_origin(monkeypatch):
    # Upstream integration modules set development flags during collection.
    # Defaults are tested with those explicit overrides absent.
    for name in ("AUTH_ENABLED", "AUTH_PROVIDER", "STORAGE_BACKEND", "DEPLOYMENT_MODE",
                 "APP_AUTO_CREATE_TABLES", "APP_AUTO_SEED_DEMO", "APP_RUN_ACTIVITY_ENGINE",
                 "ACTIVITY_USE_REDIS_NOTIFY", "LLM_PROVIDER", "LLM_MODEL", "LLM_REQUIRED",
                 "UPLOAD_DIR", "CODE_SANDBOX_BACKEND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("JWT_SECRET_KEY", "synthetic-secret-at-least-32-characters")
    config = Settings(_env_file=None, environment="production",
        database_url="postgresql://owner:fake@pool.supabase.com:5432/postgres",
        supabase_url="https://example.supabase.co", supabase_publishable_key="fake-public",
        supabase_service_role_key="fake-server", encryption_key="fake-key",
        cors_origins="https://family.example.com")
    assert config.auth_enabled and config.auth_provider == "supabase"
    assert config.storage_backend == "supabase" and config.deployment_mode == "multi_user"
    assert config.app_run_activity_engine and not config.activity_use_redis_notify
    assert not config.app_auto_create_tables and not config.app_auto_seed_demo
    assert config.llm_provider == "openai" and config.llm_required
    assert config.code_sandbox_backend == "disabled"


def test_render_generated_key_encrypts_and_decrypts(monkeypatch):
    import base64
    from libs import encryption
    # Synthetic 256-bit base64 value, matching Render generateValue's format.
    monkeypatch.setattr(encryption.settings, "encryption_key", base64.b64encode(bytes(range(32))).decode())
    monkeypatch.setattr(encryption, "_init_done", False)
    monkeypatch.setattr(encryption, "_fernet", None)
    encrypted = encryption.encrypt_value("synthetic-integration-token")
    assert encrypted.startswith("enc:")
    assert encryption.decrypt_value(encrypted) == "synthetic-integration-token"


def test_cloud_configuration_requires_private_storage_and_auth():
    with pytest.raises(ValueError, match="SUPABASE"):
        Settings(_env_file=None, auth_provider="supabase", auth_enabled=True)


def test_native_postgres_types_preserve_orm_contract():
    assert str(CompatUUID().compile(dialect=postgresql.dialect())) == "UUID"
    assert str(CompatJSONB().compile(dialect=postgresql.dialect())) == "JSONB"
    assert str(CompatUUID().compile(dialect=sqlite.dialect())) == "VARCHAR(36)"
