from pathlib import Path
from unittest.mock import patch
import tempfile
import shutil
from ai_framework.cli.main import main as cli_main
from ai_framework.tools.scaffold import list_templates


def test_cli_new_crud_delegates_without_example():
    with patch("ai_framework.cli.main.scaffold_crud") as mock_scaffold:
        mock_scaffold.return_value = Path("/tmp/fake")
        rc = cli_main(["new", "foo", "--template", "crud"])
        assert rc == 0
        mock_scaffold.assert_called_once()
        args, kwargs = mock_scaffold.call_args
        assert args[0] == "foo"
        assert (
            kwargs.get("with_example") is False
            or (len(args) > 2 and args[2] is False)
            or kwargs.get("with_example", False) is False
        )
        # check that with_example=False was passed
        call_kwargs = mock_scaffold.call_args.kwargs
        assert call_kwargs.get("with_example", False) is False


def test_cli_new_crud_with_example_delegates_with_true():
    with patch("ai_framework.cli.main.scaffold_crud") as mock_scaffold:
        mock_scaffold.return_value = Path("/tmp/fake")
        rc = cli_main(["new", "foo", "--template", "crud", "--with-example"])
        assert rc == 0
        assert mock_scaffold.call_args.kwargs.get("with_example") is True


def test_cli_new_list_contains_crud(capsys):
    rc = cli_main(["new", "--list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "crud" in out
    # also direct check
    assert "crud" in list_templates()


def test_cli_new_invalid_name_exits_nonzero():
    # filesystem_only delegation check: invalid name should exit 2, not create anything
    tmp = Path(tempfile.mkdtemp())
    orig_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp)
        rc = cli_main(["new", "123-invalid", "--template", "crud"])
        assert rc == 2
        assert not (tmp / "123-invalid").exists()
    finally:
        os.chdir(orig_cwd)
        shutil.rmtree(tmp, ignore_errors=True)
