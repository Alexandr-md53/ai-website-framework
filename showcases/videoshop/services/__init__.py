"""VideoShop showcase services (S4 scope: test entities only)."""
from .entity_lifecycle import (
    RESOLUTION_CURRENT,
    RESOLUTION_NOT_FOUND,
    RESOLUTION_REDIRECT,
    CasConflict,
    EntityLifecycleService,
    EntityNotFound,
    InvalidEntityTable,
    LifecycleError,
    SlugResolution,
)

__all__ = [
    "EntityLifecycleService",
    "SlugResolution",
    "LifecycleError",
    "InvalidEntityTable",
    "EntityNotFound",
    "CasConflict",
    "RESOLUTION_CURRENT",
    "RESOLUTION_REDIRECT",
    "RESOLUTION_NOT_FOUND",
]
