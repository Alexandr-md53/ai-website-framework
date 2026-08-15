"""
Version information for AI Website Framework.
"""

VERSION_MAJOR = 0
VERSION_MINOR = 1
VERSION_PATCH = 0

VERSION = (
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
)

__version__ = ".".join(str(part) for part in VERSION)


def get_version() -> str:
    """
    Return the current Framework version.
    """

    return __version__
