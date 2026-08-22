class DomainError(Exception):
    """Базовое исключение доменного слоя."""

    pass


class DomainValidationError(DomainError):
    """Вызывается при нарушении бизнес-инвариантов домена."""

    pass


class InvalidStateTransitionError(DomainError):
    """Вызывается при попытке недопустимого перехода состояний."""

    pass
