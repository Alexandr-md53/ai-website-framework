import pytest
from ai_framework.crud_ui.config import FieldUIConfig, CrudUIConfig


def test_config_immutability():
    field_cfg = FieldUIConfig(field_name="title", visible=True, sortable=False)
    config = CrudUIConfig(entity_name="Article", field_configs=(field_cfg,))

    with pytest.raises(AttributeError):
        config.entity_name = "Other"  # type: ignore


def test_field_config_overrides():
    field_cfg = FieldUIConfig(field_name="content", visible=False, sortable=True)
    assert field_cfg.visible is False
    assert field_cfg.sortable is True
