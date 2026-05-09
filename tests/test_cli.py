from typer.testing import CliRunner

from llmonadepress.cli import app

runner = CliRunner()


def test_devices_list():
    result = runner.invoke(app, ["devices", "list"])
    assert result.exit_code == 0
    assert "remarkable_ppm" in result.stdout


def test_sources_list_no_config(tmp_path):
    """sources list with a minimal config that has no sources."""
    config = tmp_path / "config.toml"
    config.write_text("")
    result = runner.invoke(app, ["sources", "list", "--config", str(config)])
    assert result.exit_code == 0
    assert "no sources configured" in result.stdout


def test_init_help():
    """init command should show up in help."""
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "Initialize" in result.stdout


def test_run_help():
    """run command should show up in help."""
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "--no-deliver" in result.stdout
