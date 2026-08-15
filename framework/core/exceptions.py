"""
Custom exceptions for AI Website Framework.

This module contains only Framework-specific exception classes.
It must not contain business logic or import other Framework modules.
"""


class FrameworkError(Exception):
    """
    Base exception for all AI Website Framework errors.
    """


class RegistrationError(FrameworkError):
    """
    Raised when a Framework module cannot be registered.
    """


class DuplicateRegistrationError(RegistrationError):
    """
    Raised when an item is registered more than once
    in the same registry category.
    """


class ItemNotFoundError(FrameworkError):
    """
    Raised when a requested registered item does not exist.
    """


class ModuleLoadError(FrameworkError):
    """
    Raised when a Framework module cannot be loaded.
    """


class ConfigurationError(FrameworkError):
    """
    Raised when Framework configuration is missing or invalid.
    """


class ValidationError(FrameworkError):
    """
    Исключение для ошибок валидации данных.
    """

    pass


class AIServiceError(FrameworkError):
    """
    Исключение для ошибок при работе с AI-провайдерами.
    """

    pass
