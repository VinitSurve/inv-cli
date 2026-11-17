"""Mocked execution tests for all scanners ensuring complete coverage."""

import json
from pathlib import Path
from unittest.mock import patch

from inv.config import InvConfig
from inv.constants import ScannerStatus
from inv.scanners.base import ScanContext
from inv.scanners.containers.docker import DockerScanner
from inv.scanners.extensions.ide import IdeExtensionScanner
from inv.scanners.package_managers.bun import BunGlobalScanner
from inv.scanners.package_managers.cargo import CargoScanner
from inv.scanners.package_managers.composer import ComposerScanner
from inv.scanners.package_managers.gem import GemScanner
from inv.scanners.package_managers.macports import MacPortsScanner
from inv.scanners.package_managers.yarn import YarnGlobalScanner
from inv.utils.process import ProcessResult


def test_cargo_scanner_mocked() -> None:
    scanner = CargoScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.cargo.run_command") as mock_run,
    ):
        mock_run.side_effect = [
            ProcessResult(
                argv=["cargo", "install", "--list"],
                exit_code=0,
                stdout="ripgrep v14.1.0:\n    rg\n",
                stderr="",
            ),
            ProcessResult(
                argv=["rustup", "toolchain", "list"],
                exit_code=0,
                stdout="stable-aarch64-apple-darwin (active, default)\n",
                stderr="",
            ),
        ]
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 1
        assert res.installations[0].name == "ripgrep"
        assert res.installations[0].version == "14.1.0"
        assert len(res.environments) == 1


def test_gem_scanner_mocked() -> None:
    scanner = GemScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.gem.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["gem", "list", "--local"],
            exit_code=0,
            stdout="bundler (default: 2.4.12, 2.5.0)\nrails (7.1.3)\n",
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 3


def test_composer_scanner_mocked() -> None:
    scanner = ComposerScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    mock_json = json.dumps(
        {
            "installed": [
                {
                    "name": "laravel/installer",
                    "version": "v5.5.0",
                    "description": "Laravel installer",
                }
            ]
        }
    )
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.composer.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["composer", "global", "show"],
            exit_code=0,
            stdout=mock_json,
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 1
        assert res.installations[0].name == "laravel/installer"


def test_macports_scanner_mocked() -> None:
    scanner = MacPortsScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.macports.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["port", "installed"],
            exit_code=0,
            stdout="The following ports are currently installed:\n  bash @5.2.26_0 (active)\n",
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 1
        assert res.installations[0].name == "bash"
        assert res.installations[0].version == "5.2.26_0"


def test_bun_scanner_mocked(temp_dir: Path) -> None:
    scanner = BunGlobalScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.bun.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["bun", "pm", "ls", "-g"],
            exit_code=0,
            stdout="├── prettier@3.2.5\n└── eslint@8.57.0\n",
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 2


def test_yarn_scanner_mocked() -> None:
    scanner = YarnGlobalScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.package_managers.yarn.run_command") as mock_run,
    ):
        mock_run.return_value = ProcessResult(
            argv=["yarn", "global", "list", "--json"],
            exit_code=0,
            stdout='{"type":"info","data":"create-react-app@5.0.1"}\n',
            stderr="",
        )
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.installations) == 1
        assert res.installations[0].name == "create-react-app"


def test_docker_scanner_mocked() -> None:
    scanner = DockerScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())
    with (
        patch.object(scanner, "is_available", return_value=True),
        patch("inv.scanners.containers.docker.run_command") as mock_run,
    ):
        mock_run.side_effect = [
            # 1. Probe
            ProcessResult(
                argv=["docker", "info"], exit_code=0, stdout="Server Version: 24.0.5", stderr=""
            ),
            # 2. Containers
            ProcessResult(
                argv=["docker", "ps"],
                exit_code=0,
                stdout='{"ID":"abc123456789","Names":"web-server","Image":"nginx:latest","Status":"Up 2 hours","CreatedAt":"2026-11-10","Ports":"80/tcp"}\n',
                stderr="",
            ),
            # 3. Images
            ProcessResult(
                argv=["docker", "images"],
                exit_code=0,
                stdout='{"ID":"def987654321","Repository":"nginx","Tag":"latest","CreatedAt":"2026-10-01"}\n',
                stderr="",
            ),
        ]
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.containers) == 1
        assert res.containers[0].name == "web-server"
        assert len(res.container_images) == 1
        assert res.container_images[0].repository == "nginx"


def test_ide_extensions_scanner(temp_dir: Path) -> None:
    ext_dir = temp_dir / ".vscode" / "extensions" / "ms-python.python-2024.2.1"
    ext_dir.mkdir(parents=True)
    (ext_dir / "package.json").write_text(
        json.dumps({"name": "python", "publisher": "ms-python", "version": "2024.2.1"}),
        encoding="utf-8",
    )

    scanner = IdeExtensionScanner()
    ctx = ScanContext(session_id="test", config=InvConfig())

    with patch("inv.scanners.extensions.ide.Path.home", return_value=temp_dir):
        res = scanner.execute(ctx)
        assert res.status == ScannerStatus.SUCCESS
        assert len(res.extensions) == 1
        assert res.extensions[0].name == "python"
        assert res.extensions[0].publisher == "ms-python"
