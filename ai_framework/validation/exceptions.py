class ValidationException(Exception):
    """Базовое исключение для Validation Engine."""

    pass


class InvalidSchemaError(ValidationException):
    """Вызывается, если предоставленная схема имеет невалидный формат."""

    pass


class UnknownValidatorError(ValidationException):
    """Вызывается при попытке использовать незарегистрированное правило."""

    pass


class ValidatorAlreadyExistsError(ValidationException):
    """Вызывается при попытке зарегистрировать валидатор с существующим именем."""

    pass


class EntitySchemaNotFoundError(ValidationException):
    """Вызывается, если Metadata Engine не содержит схему для указанной сущности."""

    pass
