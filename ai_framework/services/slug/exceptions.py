"""
Slug Service Exception Hierarchy (ADR-006).
"""

from ai_framework.core.exceptions import AIFrameworkError


class SlugError(AIFrameworkError):
    """Base exception for all slug service errors."""


class SlugGenerationError(SlugError):
    """Raised when a slug cannot be generated from the given input."""


class SlugCollisionError(SlugError):
    """Raised when a unique slug cannot be resolved within maximum attempts."""
