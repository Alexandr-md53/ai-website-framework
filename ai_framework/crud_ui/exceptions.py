class CrudUIError(Exception):
    """Base exception for CRUD UI subsystem errors."""


class InvalidActionScopeError(CrudUIError):
    """Raised when an ActionType is paired with an incompatible ActionScope."""
