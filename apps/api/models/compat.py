"""SQLite-only model type aliases.

`Compat*` names are kept for backwards compatibility with existing model code.
"""

import json as _json
import uuid as _uuid

from sqlalchemy import JSON, String, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB


class CompatUUID(TypeDecorator):
    """Store UUIDs as 36-char strings in SQLite."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(UUID(as_uuid=True) if dialect.name == "postgresql" else String(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            return _uuid.UUID(str(value)) if dialect.name == "postgresql" else str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return _uuid.UUID(str(value))
        return value


class CompatJSONB(TypeDecorator):
    """JSON for local databases, native JSONB for PostgreSQL."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(JSONB() if dialect.name == "postgresql" else JSON())
CompatTSVECTOR = Text


class _VectorType(TypeDecorator):
    """Store float vectors as JSON text in SQLite, auto-serialize/deserialize."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536):
        super().__init__()
        self.dim = dim

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return _json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return value
        return _json.loads(value)


class _TextVectorFactory:
    """Keep CompatVector(1536) call-shape while returning proper TypeDecorator."""

    def __call__(self, dim: int = 1536):
        return _VectorType(dim)


CompatVector = _TextVectorFactory()
