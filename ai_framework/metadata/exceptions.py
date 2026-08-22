class MetadataEngineError(Exception):
    """Base exception for all metadata engine errors."""


class MetadataNotFoundError(MetadataEngineError):
    """Raised when metadata for a requested entity/form is not registered."""


class DuplicateMetadataError(MetadataEngineError):
    """Raised when attempting to register an already existing entity metadata."""


class InvalidMetadataConfigurationError(MetadataEngineError):
    """Raised when metadata configuration or raw fragments are invalid."""
