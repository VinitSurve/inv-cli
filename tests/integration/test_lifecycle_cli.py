"""CLI smoke and integration tests for new package lifecycle and security commands."""

from typer.testing import CliRunner

from inv.cli import app

runner = CliRunner()


def test_cli_plan_install() -> None:
    res = runner.invoke(app, ["plan", "install", "ripgrep", "--manager", "brew"])
    assert res.exit_code == 0
    assert "INV PLAN — INSTALLATION" in res.output
    assert "ripgrep" in res.output
    assert "brew_formula" in res.output
    assert "No changes have been made yet" in res.output


def test_cli_plan_remove() -> None:
    res = runner.invoke(app, ["plan", "remove", "python", "--manager", "brew"])
    assert res.exit_code == 0
    assert "INV PLAN — REMOVAL" in res.output
    assert "python" in res.output


def test_cli_plan_upgrade() -> None:
    res = runner.invoke(app, ["plan", "upgrade", "ripgrep", "--manager", "brew"])
    assert res.exit_code == 0
    assert "INV PLAN — UPGRADE" in res.output
    assert "ripgrep" in res.output


def test_cli_install_dry_run() -> None:
    res = runner.invoke(app, ["install", "ripgrep", "--manager", "brew", "--dry-run"])
    assert res.exit_code == 0
    assert "Dry run requested" in res.output


def test_cli_remove_dry_run() -> None:
    res = runner.invoke(app, ["remove", "ripgrep", "--manager", "brew", "--dry-run"])
    assert res.exit_code == 0
    assert "Dry run requested" in res.output


def test_cli_upgrade_dry_run() -> None:
    res = runner.invoke(app, ["upgrade", "ripgrep", "--manager", "brew", "--dry-run"])
    assert res.exit_code == 0
    assert "Dry run requested" in res.output


def test_cli_why() -> None:
    res = runner.invoke(app, ["why", "python"])
    assert res.exit_code == 0
    assert "Dependency Analysis" in res.output
    assert "python" in res.output


def test_cli_operations_history() -> None:
    res = runner.invoke(app, ["operations"])
    assert res.exit_code == 0


def test_cli_outdated() -> None:
    res = runner.invoke(app, ["outdated", "--manager", "conda"])
    assert res.exit_code == 0
