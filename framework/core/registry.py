"""
Universal Registry for AI Website Framework.

Stores registered Framework modules by category and name.
"""

from framework.core.exceptions import (
    DuplicateRegistrationError,
    ItemNotFoundError,
)


class Registry:
    """
    Central registry for Framework modules.
    """

    def __init__(self):
        self._items = {}

    def register(self, category, name, item):
        """
        Register an item inside a category.
        """

        if category not in self._items:
            self._items[category] = {}

        if name in self._items[category]:
            raise DuplicateRegistrationError(
                f"Item '{name}' is already registered in category '{category}'."
            )

        self._items[category][name] = item

    def get(self, category, name):
        """
        Return a registered item.
        """

        category_items = self._items.get(category, {})

        if name not in category_items:
            raise ItemNotFoundError(f"Unknown item '{name}' in category '{category}'.")

        return category_items[name]

    def has(self, category, name):
        """
        Check whether an item is registered.
        """

        return name in self._items.get(category, {})

    def list(self, category):
        """
        Return all items registered inside a category.
        """

        return self._items.get(category, {}).copy()


"""
Plugin Registry for AI Website Framework.
"""
from typing import Dict, Any
from framework.core.exceptions import FrameworkError


class PluginRegistry:
    """
    Реестр для регистрации и получения плагинов фреймворка.
    """

    def __init__(self):
        self._plugins: Dict[str, Any] = {}

    def register(self, name: str, plugin_instance: Any) -> None:
        """Регистрирует новый плагин под уникальным именем."""
        if not name:
            raise FrameworkError("Имя плагина не может быть пустым.")
        self._plugins[name] = plugin_instance

    def get_plugin(self, name: str) -> Any:
        """Возвращает плагин по имени."""
        if name not in self._plugins:
            raise FrameworkError(f"Плагин '{name}' не найден в реестре.")
        return self._plugins[name]

    def list_plugins(self) -> list[str]:
        """Возвращает список имён всех зарегистрированных плагинов."""
        return list(self._plugins.keys())


registry = Registry()
