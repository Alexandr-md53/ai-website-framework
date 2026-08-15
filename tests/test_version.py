"""
Tests for Framework version information.
"""

from framework.core.version import (
    VERSION,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
    __version__,
    get_version,
)


def test_version_parts():
    assert VERSION_MAJOR == 0
    assert VERSION_MINOR == 1
    assert VERSION_PATCH == 0


def test_version_tuple():
    assert VERSION == (0, 1, 0)


def test_version_string():
    assert __version__ == "0.1.0"


def test_get_version_returns_version_string():
    assert get_version() == "0.1.0"
