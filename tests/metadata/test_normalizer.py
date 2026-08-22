from types import MappingProxyType
import pytest

from ai_framework.metadata.exceptions import InvalidMetadataConfigurationError
from ai_framework.metadata.normalizer import normalize_opaque_value


def test_normalize_primitives():
    assert normalize_opaque_value("string") == "string"
    assert normalize_opaque_value(42) == 42
    assert normalize_opaque_value(3.14) == 3.14
    assert normalize_opaque_value(True) is True
    assert normalize_opaque_value(None) is None


def test_normalize_list_to_tuple_recursively():
    input_data = [1, "a", [2, 3]]
    result = normalize_opaque_value(input_data)

    assert isinstance(result, tuple)
    assert result == (1, "a", (2, 3))


def test_normalize_dict_to_mapping_proxy_recursively():
    input_data = {"key": "value", "nested": {"a": 1}}
    result = normalize_opaque_value(input_data)

    assert isinstance(result, MappingProxyType)
    assert result["key"] == "value"
    assert isinstance(result["nested"], MappingProxyType)
    assert result["nested"]["a"] == 1

    with pytest.raises(TypeError):
        result["key"] = "new_value"  # type: ignore


def test_reject_unsupported_non_json_types():
    class CustomObject:
        pass

    with pytest.raises(InvalidMetadataConfigurationError):
        normalize_opaque_value(CustomObject())

    with pytest.raises(InvalidMetadataConfigurationError):
        normalize_opaque_value(lambda x: x)
