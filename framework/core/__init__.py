"""
Core modules of AI Website Framework.
"""

from framework.core.contracts import (
    FrameworkComponent,
    GeneratorContract,
    PublisherContract,
)
from framework.core.exceptions import (
    ConfigurationError,
    DuplicateRegistrationError,
    FrameworkError,
    ItemNotFoundError,
    ModuleLoadError,
    RegistrationError,
)
from framework.core.loader import ComponentLoader, loader
from framework.core.registry import Registry, registry
from framework.core.settings import Settings, settings
from framework.core.version import (
    VERSION,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    __version__,
    get_version,
)

__all__ = [
    "ComponentLoader",
    "ConfigurationError",
    "DuplicateRegistrationError",
    "FrameworkComponent",
    "FrameworkError",
    "GeneratorContract",
    "ItemNotFoundError",
    "ModuleLoadError",
    "PublisherContract",
    "RegistrationError",
    "Registry",
    "Settings",
    "VERSION",
    "VERSION_MAJOR",
    "VERSION_MINOR",
    "VERSION_PATCH",
    "__version__",
    "get_version",
    "loader",
    "registry",
    "settings",
]

from framework.core.persistence import (
    BaseRepository,
    InMemoryRepository,
    PageResult,
    Pagination,
    UnitOfWork,
)

__all__ = [
    "BaseRepository",
    "UnitOfWork",
    "Pagination",
    "PageResult",
    "InMemoryRepository",
]
