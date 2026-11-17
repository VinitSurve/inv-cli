"""Unit tests for version parsing and extraction."""

from inv.utils.versions import extract_version, parse_version


def test_extract_version() -> None:
    assert extract_version("Python 3.11.7") == "3.11.7"
    assert extract_version("git version 2.39.5 (Apple Git-154)") == "2.39.5"
    assert extract_version("Docker version 27.2.0, build 3ab4256") == "27.2.0"
    assert extract_version("v1.2.3-rc1") == "1.2.3-rc1"
    assert extract_version("no version here") is None
    assert extract_version("") is None


def test_parse_version() -> None:
    pv = parse_version("v3.11.2-alpha")
    assert pv is not None
    assert pv.major == 3
    assert pv.minor == 11
    assert pv.patch == 2
    assert pv.prerelease == "alpha"

    assert parse_version("invalid-string") is None
    assert parse_version(None) is None

