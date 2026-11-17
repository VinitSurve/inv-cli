"""Smoke tests verifying all CLI commands execute cleanly."""

from typer.testing import CliRunner

from inv.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    assert "A comprehensive macOS-first software inventory tool" in res.output


def test_cli_version() -> None:
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0
    assert "Inventory CLI version" in res.output


def test_cli_default_overview() -> None:
    res = runner.invoke(app, [])
    assert res.exit_code == 0


def test_cli_doctor() -> None:
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "Diagnostics & Doctor" in res.output


def test_cli_config() -> None:
    res = runner.invoke(app, ["config"])
    assert res.exit_code == 0
    assert "Configuration" in res.output


def test_cli_managers() -> None:
    res = runner.invoke(app, ["managers"])
    assert res.exit_code == 0
    assert "Package Manager Detection Status" in res.output


def test_cli_tools() -> None:
    res = runner.invoke(app, ["tools"])
    assert res.exit_code == 0


def test_cli_duplicates() -> None:
    res = runner.invoke(app, ["duplicates"])
    assert res.exit_code == 0
    assert "Duplication & Shadowing" in res.output


def test_cli_apps() -> None:
    res = runner.invoke(app, ["apps"])
    assert res.exit_code == 0


def test_cli_runtimes() -> None:
    res = runner.invoke(app, ["runtimes"])
    assert res.exit_code == 0


def test_cli_envs() -> None:
    res = runner.invoke(app, ["envs"])
    assert res.exit_code == 0


def test_cli_containers() -> None:
    res = runner.invoke(app, ["containers"])
    assert res.exit_code == 0


def test_cli_stats() -> None:
    res = runner.invoke(app, ["stats"])
    assert res.exit_code == 0


def test_cli_report() -> None:
    res = runner.invoke(app, ["report"])
    assert res.exit_code == 0


def test_cli_tree() -> None:
    res = runner.invoke(app, ["tree"])
    assert res.exit_code == 0


def test_cli_export_json() -> None:
    res = runner.invoke(app, ["export", "--format", "json"])
    assert res.exit_code == 0
    assert "session" in res.output


def test_cli_export_csv() -> None:
    res = runner.invoke(app, ["export", "--format", "csv"])
    assert res.exit_code == 0
    assert "Name,Version,Manager" in res.output


def test_cli_export_html() -> None:
    res = runner.invoke(app, ["export", "--format", "html"])
    assert res.exit_code == 0
    assert "<!DOCTYPE html>" in res.output


def test_cli_search() -> None:
    res = runner.invoke(app, ["search", "python"])
    assert res.exit_code == 0


def test_cli_info() -> None:
    res = runner.invoke(app, ["info", "python"])
    assert res.exit_code == 0
