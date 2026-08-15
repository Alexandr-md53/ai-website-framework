"""
Core contracts for AI Website Framework.

Contracts define the required public interface for Framework modules.
They describe what a module must provide, without containing
business-specific implementation.
"""

from abc import ABC, abstractmethod
from typing import Any


class FrameworkComponent(ABC):
    """
    Base contract for all Framework components.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the unique component name.
        """

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        Execute the component using the provided data.
        """


class GeneratorContract(FrameworkComponent):
    """
    Contract for content generators.
    """

    @abstractmethod
    def generate(self, data: Any) -> Any:
        """
        Generate content from the provided data.
        """

    def execute(self, data: Any) -> Any:
        """
        Execute the generator through the common component interface.
        """

        return self.generate(data)


class PublisherContract(FrameworkComponent):
    """
    Contract for publication modules.
    """

    @abstractmethod
    def publish(self, data: Any) -> Any:
        """
        Publish the provided data to a target channel.
        """

    def execute(self, data: Any) -> Any:
        """
        Execute the publisher through the common component interface.
        """

        return self.publish(data)
