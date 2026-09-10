from ai_framework.cli.main import main as cli_main
from ai_framework.api.registry import clear_cache


def test_cli_product_list_via_registry(capsys):
    clear_cache()
    code = cli_main(["product", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "cafe" in out
    assert "lawyer" in out
    assert "plant_nursery" in out


def test_cli_showcase_list_via_registry(capsys):
    clear_cache()
    code = cli_main(["showcase", "list"])
    assert code == 0
    out = capsys.readouterr().out
    assert "cafe" in out
    assert "found" in out


def test_cli_showcase_info_via_registry(capsys):
    clear_cache()
    code = cli_main(["showcase", "info", "cafe"])
    assert code == 0
    out = capsys.readouterr().out
    assert "cafe" in out
    assert "crud" in out
    assert "manifest.json" in out


def test_cli_showcase_info_invalid():
    clear_cache()
    code = cli_main(["showcase", "info", "nonexistent"])
    assert code == 1
