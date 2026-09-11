from ai_framework.cli.main import main as cli_main
from ai_framework.api import inspect_project
from pathlib import Path
import json


def test_api_inspect_export():
    assert callable(inspect_project)


def test_cli_inspect_text(capsys):
    # inspect showcase cafe - should exist
    target = Path("showcases/cafe")
    if not target.exists():
        target = Path.cwd() / "showcases" / "cafe"
    code = cli_main(["inspect", str(target)])
    assert code == 0
    out = capsys.readouterr().out
    assert "manifest.json" in out or "cafe" in out


def test_cli_inspect_json(capsys):
    target = Path("showcases/cafe")
    if not target.exists():
        target = Path.cwd() / "showcases" / "cafe"
    code = cli_main(["inspect", str(target), "--json"])
    assert code == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert isinstance(data, dict)
