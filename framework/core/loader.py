"""
Component loader for AI Website Framework.

Validates Framework components and registers them
in the central Registry.
"""

from framework.core.contracts import FrameworkComponent
from framework.core.exceptions import ModuleLoadError
from framework.core.registry import Registry, registry


class ComponentLoader:
    """
    Loads Framework components into a Registry.
    """

    def __init__(self, target_registry: Registry | None = None):
        self._registry = target_registry or registry

    def load(
        self,
        category: str,
        component: FrameworkComponent,
    ) -> FrameworkComponent:
        """
        Validate and register one Framework component.
        """

        if not isinstance(component, FrameworkComponent):
            raise ModuleLoadError("Loaded object must implement FrameworkComponent.")

        component_name = component.name

        if not isinstance(component_name, str):
            raise ModuleLoadError("Component name must be a string.")

        if not component_name.strip():
            raise ModuleLoadError("Component name cannot be empty.")

        try:
            self._registry.register(
                category=category,
                name=component_name,
                item=component,
            )
        except Exception as error:
            raise ModuleLoadError(
                f"Could not load component "
                f"'{component_name}' into category '{category}'."
            ) from error

        return component


loader = ComponentLoader()
