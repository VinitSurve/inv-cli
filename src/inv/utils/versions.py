"""Version extraction and parsing utilities."""

import re
from typing import NamedTuple

VERSION_PATTERN = re.compile(
    r"""
    v?
    (?P<major>\d+)
    (?:\.(?P<minor>\d+))?
    (?:\.(?P<patch>\d+))?
    (?:[-._]?(?P<prerelease>[0-9A-Za-z.-]+))?
    """,
    re.VERBOSE,
)


class ParsedVersion(NamedTuple):
    """Normalized components of a parsed version."""

    major: int
    minor: int
    patch: int
    prerelease: str
    raw: str


def extract_version(text: str) -> str | None:
    """Extract the first semver-like version substring from arbitrary tool output."""
    if not text:
        return None

    # Search line by line to avoid multi-line noise
    for line in text.splitlines():
        line = line.strip()
        match = re.search(r"\b(?:v)?(\d+\.\d+(?:\.\d+)?(?:[-._][0-9A-Za-z.-]+)?)\b", line)
        if match:
            return match.group(1).lstrip("v")
    return None


def parse_version(version_str: str | None) -> ParsedVersion | None:
    """Parse a version string into comparable numerical components."""
    if not version_str:
        return None

    clean = version_str.strip().lstrip("v")
    match = VERSION_PATTERN.search(clean)
    if not match:
        return None

    groups = match.groupdict()
    major = int(groups.get("major") or 0)
    minor = int(groups.get("minor") or 0)
    patch = int(groups.get("patch") or 0)
    prerelease = groups.get("prerelease") or ""

    return ParsedVersion(
        major=major,
        minor=minor,
        patch=patch,
        prerelease=prerelease,
        raw=version_str,
    )

