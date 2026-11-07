"""Keep application tables inaccessible through Supabase's public Data API.

FastAPI connects as the database owner and enforces application ownership.
No browser Data API policies are installed: JWT authentication alone must not
grant access to all family documents or student results.
"""
from alembic import op
import sqlalchemy as sa

revision = "20261107_0027"
down_revision = "20261028_0026"
branch_labels = None
depends_on = None

# Frozen list: never iterate over unrelated tables in a shared schema.
TABLES = (
    "users", "courses", "course_content_tree", "user_preferences", "preference_signals",
    "practice_problems", "practice_results", "conversation_memories", "ingestion_jobs",
    "study_sessions", "assignments", "wrong_answers", "learning_progress", "learning_templates",
    "scrape_sources", "auth_sessions", "chat_sessions", "chat_message_logs", "generated_assets",
    "study_plans", "study_goals", "agent_tasks", "agenda_runs", "agent_kv", "mastery_snapshots",
    "integration_credentials", "knowledge_nodes", "knowledge_edges", "concept_mastery",
    "notifications", "cognitive_baselines", "usage_events", "intervention_outcomes",
)


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    roles = set(bind.execute(sa.text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")).scalars())
    for table in TABLES:
        if table not in existing:
            continue
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        for role in sorted(roles):
            op.execute(f'REVOKE ALL ON TABLE "{table}" FROM "{role}"')


def downgrade():
    # Deliberately preserve privacy on rollback; reopening the Data API requires
    # an explicit administrative decision outside this migration.
    pass
