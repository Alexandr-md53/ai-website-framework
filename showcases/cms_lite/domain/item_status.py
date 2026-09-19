from enum import Enum
class ItemStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class InvalidStateTransitionError(Exception):
    pass
