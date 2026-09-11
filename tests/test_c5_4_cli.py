from ai_framework.cli.main import main as cli_main
from ai_framework.api.registry import clear_cache
import json


def test_cli_version(capsys):
    clear_cache()
    code = cli_main(["version"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    assert "10.2" in out


def test_cli_product_info_alias(capsys):
    clear_cache()
    code = cli_main(["product", "info", "cafe"])
    assert code == 0
    out = capsys.readouterr().out
    assert "cafe" in out
    assert "crud" in out


def test_cli_product_info_invalid():
    clear_cache()
    code = cli_main(["product", "info", "nonexistent"])
    assert code == 1


def test_cli_json_list(capsys):
    clear_cache()
    code = cli_main(["product", "list", "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert isinstance(data, list)
    names = {d["name"] for d in data}
    assert {"cafe", "lawyer", "plant_nursery"}.issubset(names)
    # minimal contract - only 4 fields
    for d in data:
        assert set(d.keys()) == {"name", "product", "version", "package"}


def test_cli_json_info(capsys):
    clear_cache()
    code = cli_main(["showcase", "info", "cafe", "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["name"] == "cafe"
    assert data["product"] == "crud"
    assert "version" in data
    assert "package" in data
