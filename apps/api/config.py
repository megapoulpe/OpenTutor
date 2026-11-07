"""Application configuration via environment variables."""

import os
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files(config_file: Path) -> tuple[str, ...]:
    api_dir = config_file.parent
    if api_dir.name == "api" and api_dir.parent.name == "apps":
        return (str(api_dir.parent.parent / ".env"), ".env")
    return (".env",)


class Settings(BaseSettings):
    environment: str = "development"

    # PostgreSQL for deployment; upstream SQLite remains available in development.
    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"

    # LLM — primary provider selection
    llm_provider: str = "ollama"  # ollama | openai | anthropic | deepseek | openrouter | gemini | groq | vllm | lmstudio | textgenwebui | custom
    llm_model: str = "llama3.2:3b"

    # Cloud providers
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    openrouter_api_key: str = ""
    gemini_api_key: str = ""
    groq_api_key: str = ""

    # Local inference backends
    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8000/v1"
    lmstudio_base_url: str = "http://localhost:1234/v1"
    textgenwebui_base_url: str = "http://localhost:5000/v1"

    # Generic OpenAI-compatible endpoint
    custom_llm_api_key: str = ""
    custom_llm_base_url: str = ""
    custom_llm_model: str = ""

    # LiteLLM integration (opt-in alternative provider)
    use_litellm: bool = False
    litellm_model: str = ""  # Model string for LiteLLM (e.g., "openai/gpt-4o")
    litellm_api_base: str = ""  # Optional custom API base for LiteLLM proxy
    litellm_api_key: str = ""  # Optional API key for LiteLLM proxy

    # Model size routing (agent preference hints)
    llm_model_large: str = ""   # e.g. gpt-4o for teaching/planning agents
    llm_model_small: str = ""   # e.g. gpt-4o-mini for preference/scene agents
    llm_required: bool = False

    # 3-tier model routing (overrides large/small when set)
    llm_model_fast: str = ""       # e.g. gpt-4o-mini — greetings, preferences
    llm_model_standard: str = ""   # e.g. gpt-4o — teaching, exercises
    llm_model_frontier: str = ""   # e.g. o3-mini — planning, code execution

    # Authentication
    auth_enabled: bool = False
    auth_provider: str = "local"  # local | supabase
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "documents"
    storage_backend: str = "local"  # local | supabase
    allowed_upload_extensions: str = ".pdf,.pptx,.ppt,.docx,.doc,.html,.htm,.txt,.md"
    deployment_mode: str = "single_user"  # single_user | multi_user
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3001,http://127.0.0.1:3001"

    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50
    scrape_fixture_dir: str = ""

    # Embedding
    embedding_mode: str = "auto"  # auto | eager | skip
    # auto  = use fast provider if available, skip if only slow local provider
    # eager = always compute embeddings (blocks ingestion if slow)
    # skip  = never compute embeddings (search uses keyword-only fallback)

    # Runtime bootstrap
    app_auto_create_tables: bool = True
    app_auto_seed_system: bool = True
    app_auto_seed_demo: bool = True
    app_run_scheduler: bool = False
    app_run_activity_engine: bool = False
    ambient_monitor_enabled: bool = True
    enable_experimental_loom: bool = False
    enable_experimental_lector: bool = False
    enable_experimental_notion_export: bool = False
    enable_experimental_cat: bool = False              # CAT adaptive diagnostic pretest
    enable_experimental_browser: bool = False          # Browser automation (web_search agent tool)
    enable_experimental_vision: bool = False            # Vision/LaTeX OCR service
    voice_enabled: bool = False

    # Rate limiting
    rate_limit_mode: str = "simple"  # "simple" | "cost_aware"
    rate_limit_rpm: int = 120  # requests per minute per IP (simple mode)
    rate_limit_llm_rpm: int = 20  # requests per minute per IP for LLM endpoints
    rate_limit_cost_budget: int = 500  # cost units per minute per IP (cost_aware mode)
    trust_proxy_headers: bool = False  # Trust X-Forwarded-For header (only enable behind a reverse proxy)

    # SSE streaming
    sse_timeout_seconds: int = 300

    # Parallel execution
    parallel_context_loading: bool = True
    activity_engine_max_concurrency: int = 3
    activity_use_redis_notify: bool = False

    # Web search
    tavily_api_key: str = ""

    # Workspace (agent file operations)
    workspace_max_size_mb: int = 500

    # Code sandbox
    code_sandbox_backend: str = "auto"  # disabled | container | auto | process
    code_sandbox_runtime: str = "docker"  # docker | podman
    code_sandbox_timeout_seconds: int = 5
    allow_insecure_process_sandbox: bool = False  # Allows raw subprocess sandbox (no container isolation)

    # Encryption (Fernet key for at-rest encryption of OAuth tokens etc.)
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    encryption_key: str = ""

    # Cognitive load signal weights (sum = 1.0)
    # Source: "Cognitive Load Theory meets Deep Knowledge Tracing" (Nature, 2025)
    # Proportionally normalized from original paper weights to sum to 1.0
    cognitive_load_weight_fatigue: float = 0.16
    cognitive_load_weight_session_length: float = 0.08
    cognitive_load_weight_errors: float = 0.14
    cognitive_load_weight_brevity: float = 0.04
    cognitive_load_weight_help_seeking: float = 0.10
    cognitive_load_weight_quiz_performance: float = 0.10
    cognitive_load_weight_answer_hesitation: float = 0.06
    cognitive_load_weight_nlp_affect: float = 0.10
    cognitive_load_weight_relative_baseline: float = 0.08
    # Clickstream-derived signals (arXiv 2512.20438)
    cognitive_load_weight_wrong_streak: float = 0.05
    cognitive_load_weight_message_gap: float = 0.05
    cognitive_load_weight_repeated_errors: float = 0.04
    cognitive_load_threshold_high: float = 0.6
    cognitive_load_threshold_medium: float = 0.3

    # Cognitive load normalization constants
    cognitive_load_session_messages_norm: float = 40.0     # ~40 messages ≈ 45 min
    cognitive_load_error_count_norm: float = 5.0           # 5+ unmastered errors = max signal
    cognitive_load_brevity_length_norm: float = 100.0      # <100 chars = some signal
    cognitive_load_quiz_accuracy_target: float = 0.7       # Below 70% accuracy = signal
    cognitive_load_hesitation_min_ms: float = 15000.0      # 15s = no signal
    cognitive_load_hesitation_range_ms: float = 45000.0    # 60s+ = full signal
    cognitive_load_nlp_frustration_weight: float = 0.6
    cognitive_load_nlp_confusion_weight: float = 0.4
    cognitive_load_review_reorder_threshold: float = 0.5

    # LECTOR review priority factors
    lector_factor_low_mastery: float = 0.5       # Multiplier for (0.8 - mastery)
    lector_factor_never_practiced: float = 0.3   # Bonus for unpracticed concepts
    lector_factor_time_decay: float = 0.3        # Memory decay weight
    lector_factor_prerequisite: float = 0.2      # Weak prerequisite boost
    lector_factor_confusion: float = 0.1         # Confusion pair boost
    lector_mastery_threshold: float = 0.8        # Below this = needs review
    lector_prerequisite_threshold: float = 0.5   # Prereq mastery alert level
    lector_confusion_threshold: float = 0.6      # Confusion pair mastery alert
    lector_factor_interference: float = 0.15    # Proactive interference matrix weight (LECTOR paper)

    # CAT diagnostic pretest stopping criteria (issue #40)
    cat_min_items: int = 5          # Never stop before this many questions
    cat_max_items: int = 20         # Hard cap on pretest length
    cat_se_threshold: float = 0.15  # Stop early once ability standard error drops below this

    # LOOM knowledge graph parameters
    loom_fusion_similarity_threshold: float = 0.85  # Graphusion concept dedup threshold
    loom_interference_similarity_threshold: float = 0.6  # LECTOR interference matrix threshold
    loom_interference_top_n: int = 20            # Max interference pairs per course
    loom_consolidation_threshold: float = 0.85   # All prereqs must exceed this for consolidation
    loom_consolidation_parent_boost: float = 0.1 # Mastery boost when prereq group mastered
    loom_consolidation_stability_multiplier: float = 1.5  # Extend stability of mastered prereqs

    # BKT mastery parameters (pyBKT paper)
    bkt_default_p_learn: float = 0.10            # Learning transition probability
    bkt_default_slip: float = 0.10               # Default slip probability

    # FIRe bidirectional propagation (GKT paper)
    fire_doubt_per_depth: float = 0.03           # Doubt propagation per depth on incorrect

    # Logging
    log_file: str = ""  # Path to log file; empty = stdout only
    log_max_bytes: int = 10_485_760  # 10 MB
    log_backup_count: int = 5

    @model_validator(mode="before")
    @classmethod
    def _production_defaults(cls, values):
        """One deployment configuration; explicit upstream settings still win."""
        if values.get("environment") in {"production", "staging"}:
            import tempfile
            defaults = {
                "auth_enabled": True, "auth_provider": "supabase",
                "deployment_mode": "multi_user", "storage_backend": "supabase",
                "app_auto_create_tables": False, "app_auto_seed_demo": False,
                "app_run_activity_engine": True, "activity_use_redis_notify": False,
                "llm_provider": "openai", "llm_required": True,
                "upload_dir": str(Path(tempfile.gettempdir()) / "opentutor-uploads"),
                "code_sandbox_backend": "disabled",
            }
            for key, value in defaults.items():
                values.setdefault(key, value)
            if values["llm_provider"] == "openai":
                values.setdefault("llm_model", "gpt-4o-mini")
        return values

    @property
    def postgres_connect_args(self) -> dict:
        """Shared API/Alembic TLS configuration, with no remote plaintext mode."""
        from sqlalchemy.engine import make_url
        from certifi import where
        url = make_url(self.database_url)
        if self.environment == "development" and url.host in {"localhost", "127.0.0.1", "::1", "postgres"}:
            return {"sslmode": "disable"}
        root_cert = where()
        if (url.host or "").lower().endswith((".pooler.supabase.com", ".supabase.co")):
            root_cert = str(Path(__file__).resolve().parent / "certs" / "supabase-prod-ca-2021.crt")
        return {"sslmode": "verify-full", "sslrootcert": url.query.get("sslrootcert") or root_cert}

    @staticmethod
    def _split_csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return self._split_csv(self.cors_origins)

    @model_validator(mode="after")
    def _resolve_database_url(self):
        """Normalize the driver, retaining upstream SQLite development support."""
        if not self.database_url:
            if self.environment != "development":
                raise ValueError("DATABASE_URL is required outside development")
            data_dir = Path.home() / ".opentutor"
            data_dir.mkdir(parents=True, exist_ok=True)
            self.database_url = f"sqlite+aiosqlite:///{data_dir / 'data.db'}"
        elif self.database_url.startswith("sqlite"):
            for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
                if self.database_url.startswith(prefix):
                    sqlite_path = self.database_url[len(prefix):]
                    if sqlite_path.startswith("~"):
                        self.database_url = f"{prefix}{Path(sqlite_path).expanduser()}"
                    break
        elif self.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
            from sqlalchemy.engine import make_url

            url = make_url(self.database_url).set(drivername="postgresql+psycopg")
            if url.port == 6543:
                raise ValueError("Use the Supabase session pooler on port 5432, not transaction port 6543")
            self.database_url = url.render_as_string(hide_password=False)
        else:
            raise ValueError(
                "DATABASE_URL must use SQLite or PostgreSQL (psycopg)"
            )
        return self

    @model_validator(mode="after")
    def _validate_security(self):
        import logging as _logging

        _log = _logging.getLogger("opentutor.config")

        if self.auth_provider not in {"local", "supabase"}:
            raise ValueError("AUTH_PROVIDER must be local or supabase")
        if self.storage_backend not in {"local", "supabase"}:
            raise ValueError("STORAGE_BACKEND must be local or supabase")
        if self.auth_provider == "supabase":
            if not self.auth_enabled or not self.supabase_url or not self.supabase_publishable_key:
                raise ValueError("Supabase auth requires AUTH_ENABLED, SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY")
        if self.storage_backend == "supabase" and (not self.supabase_url or not self.supabase_service_role_key):
            raise ValueError("Supabase storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        if self.supabase_url and not self.supabase_url.startswith("https://"):
            if self.environment != "development" or not self.supabase_url.startswith(("http://localhost:", "http://127.0.0.1:")):
                raise ValueError("SUPABASE_URL must use HTTPS")
        if self.environment != "development" and "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must contain explicit origins in production")
        if self.max_upload_size_mb <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be positive")

        # Generate a random CSRF signing key when jwt_secret_key is not set
        # (CSRF middleware needs a signing key even when auth is disabled)
        if not self.jwt_secret_key:
            import secrets as _secrets
            self.jwt_secret_key = _secrets.token_hex(32)

        if self.auth_enabled:
            if len(self.jwt_secret_key) < 32:
                raise ValueError(
                    "jwt_secret_key must be at least 32 characters when auth is enabled"
                )
        else:
            if self.environment != "development":
                raise ValueError(
                    "AUTH_ENABLED must be true outside of development. "
                    "Running without authentication exposes all user data. "
                    "Set AUTH_ENABLED=true and JWT_SECRET_KEY (>= 32 chars)."
                )
            _log.warning(
                "SECURITY WARNING: auth_enabled=False (development mode). "
                "Anyone with network access can use this instance without authentication. "
                "Set AUTH_ENABLED=true and configure JWT_SECRET_KEY before deploying.",
            )

        if self.environment in ("production", "staging"):
            if self.storage_backend == "supabase" and not self.app_run_activity_engine:
                raise ValueError("Supabase storage requires APP_RUN_ACTIVITY_ENGINE=true for durable processing and deletion")
            if not self.auth_enabled:
                raise ValueError(
                    "AUTH_ENABLED must be true in production/staging. "
                    "Running without authentication in production is a critical security risk."
                )
            env_key = os.environ.get("JWT_SECRET_KEY", "")
            if not env_key or len(env_key) < 32:
                raise ValueError(
                    "JWT_SECRET_KEY must be explicitly set (>= 32 chars) in production with auth enabled"
                )
            if "REDACTED_DEV_PASSWORD" in self.database_url:
                raise ValueError(
                    "Default database password must be changed in production"
                )
            if not self.encryption_key:
                raise ValueError(
                    "ENCRYPTION_KEY is required in production for at-rest encryption "
                    "of sensitive data (OAuth tokens, etc.). Generate one with: "
                    "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
                )
        return self

    model_config = SettingsConfigDict(
        # Root .env is shared with Compose; a working-directory .env can override
        # it for existing native setups. Explicit process environment wins both.
        env_file=_env_files(Path(__file__).resolve()),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
