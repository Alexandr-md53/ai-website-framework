"""VideoShop infrastructure migrations (S3 scope)."""
from .runner import (
    Migration,
    MigrationError,
    UnsupportedSchemaVersion,
    migrate,
    read_schema_version,
)
from .s3 import (
    LIVE_ENTITY_UNIQUE_INDEX,
    S3_MIGRATIONS,
    SLUG_REGISTRY_DDL,
    SLUG_REGISTRY_INDEX,
    LiveSlugDuplicatesError,
)

__all__ = [
    "Migration",
    "MigrationError",
    "UnsupportedSchemaVersion",
    "migrate",
    "read_schema_version",
    "S3_MIGRATIONS",
    "SLUG_REGISTRY_DDL",
    "SLUG_REGISTRY_INDEX",
    "LIVE_ENTITY_UNIQUE_INDEX",
    "LiveSlugDuplicatesError",
]
