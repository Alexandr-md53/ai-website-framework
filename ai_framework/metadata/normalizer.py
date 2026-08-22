from types import MappingProxyType
from typing import Any

from ai_framework.metadata.exceptions import InvalidMetadataConfigurationError

ALLOWED_PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def normalize_opaque_value(value: Any) -> Any:
    """Recursively normalizes arbitrary values into immutable JSON-compatible types.

    Primitives (str, int, float, bool, None) remain as-is.
    Lists and sets are converted to tuples.
    Dicts are converted to MappingProxyType.
    Unsupported types raise InvalidMetadataConfigurationError.
    """
    if isinstance(value, ALLOWED_PRIMITIVE_TYPES):
        return value

    if isinstance(value, (list, tuple, set)):
        return tuple(normalize_opaque_value(item) for item in value)

    if isinstance(value, (dict, MappingProxyType)):
        return MappingProxyType(
            {str(k): normalize_opaque_value(v) for k, v in value.items()}
        )

    raise InvalidMetadataConfigurationError(
        f"Unsupported opaque value type '{type(value).__name__}'. "
        f"Only JSON-compatible primitives and collections are allowed."
    )
