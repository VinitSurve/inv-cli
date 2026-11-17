"""Unit tests for configuration manager."""

from pathlib import Path

from inv.config import InvConfig


def test_default_config() -> None:
    cfg = InvConfig()
    assert cfg.scan_projects is True
    assert cfg.deep_scan is False
    assert cfg.max_depth == 5
    assert cfg.process_timeout == 15.0


def test_config_save_and_load(temp_dir: Path) -> None:
    cfg_file = temp_dir / "custom_config.json"
    cfg = InvConfig(
        scan_projects=False,
        deep_scan=True,
        max_depth=3,
        process_timeout=30.0,
        disabled_scanners=["docker", "macports"],
    )
    cfg.save(cfg_file)
    assert cfg_file.exists()

    loaded = InvConfig.load(cfg_file)
    assert loaded.scan_projects is False
    assert loaded.deep_scan is True
    assert loaded.max_depth == 3
    assert loaded.process_timeout == 30.0
    assert loaded.disabled_scanners == ["docker", "macports"]
