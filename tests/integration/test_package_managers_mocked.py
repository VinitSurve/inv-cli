"""Integration tests for package manager adapters with mocked CLI outputs."""

import json
from unittest.mock import patch

from inv.config import InvConfig
from inv.constants import ScannerStatus
from inv.scanners.base import ScanContext
from inv.scanners.package_managers.brew import BrewFormulaScanner
from inv.scanners.package_managers.npm import NpmGlobalScanner
from inv.scanners.package_managers.pip import PipScanner
from inv.utils.process import ProcessResult


def test_brew_formula_scanner_mocked() -> None:
    scanner = BrewFormulaScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())

    mock_json = json.dumps(
        {
            "formulae": [
                {
                    "name": "ripgrep",
                    "desc": "Fast grep replacement",
                    "homepage": "https://github.com/BurntSushi/ripgrep",
                    "license": "Unlicense",
                    "versions": {"stable": "14.1.0"},
                    "installed": [{"version": "14.1.0"}],
                }
            ]
        }
    )

    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.brew.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["brew", "info"],
            exit_code=0,
            stdout=mock_json,
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 1
        assert res.installations[0].name == "ripgrep"
        assert res.installations[0].version == "14.1.0"


def test_npm_global_scanner_mocked() -> None:
    scanner = NpmGlobalScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())

    mock_json = json.dumps(
        {
            "dependencies": {
                "typescript": {
                    "version": "5.3.3",
                    "path": "/usr/local/lib/node_modules/typescript",
                },
                "corepack": {"version": "0.24.0", "path": "/usr/local/lib/node_modules/corepack"},
            }
        }
    )

    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.npm.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["npm", "list"],
            exit_code=0,
            stdout=mock_json,
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 2
        names = {i.name for i in res.installations}
        assert "typescript" in names
        assert "corepack" in names


def test_pip_scanner_mocked() -> None:
    scanner = PipScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())

    mock_json = json.dumps(
        [
            {"name": "typer", "version": "0.9.0"},
            {"name": "rich", "version": "13.7.0"},
        ]
    )

    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.pip.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["pip", "list"],
            exit_code=0,
            stdout=mock_json,
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 2
        assert res.installations[0].name == "typer"
