"""Unit tests for Normalizer."""

from inv.core.normalizer import Normalizer


def test_canonical_name_python() -> None:
    assert Normalizer.canonical_name("My_Package_Name", "python") == "my-package-name"
    assert Normalizer.canonical_name("flask-cors", "python") == "flask-cors"


def test_canonical_name_npm() -> None:
    assert Normalizer.canonical_name("@babel/core", "npm") == "core"
    assert Normalizer.canonical_name("Express", "npm") == "express"


def test_clean_version() -> None:
    assert Normalizer.clean_version("v1.2.3") == "1.2.3"
    assert Normalizer.clean_version("  v2.0.0-rc1  ") == "2.0.0-rc1"
    assert Normalizer.clean_version(None) == "unknown"
    assert Normalizer.clean_version("3.11.4") == "3.11.4"
