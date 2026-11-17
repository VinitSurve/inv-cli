"""Normalization rules for software identities and versions."""


class Normalizer:
    """Normalizes package names, versions, and ecosystem identifiers."""

    @staticmethod
    def canonical_name(name: str, ecosystem: str) -> str:
        """Derive a normalized canonical name for cross-ecosystem comparison."""
        clean = name.strip().lower()
        if ecosystem == "python":
            clean = clean.replace("_", "-")
        elif ecosystem in ("npm", "yarn", "pnpm", "bun") and clean.startswith("@") and "/" in clean:
            clean = clean.split("/", 1)[1]
        return clean

    @staticmethod
    def clean_version(version: str | None) -> str:
        """Strip prefixes, v-tags, and whitespace from version string."""
        if not version:
            return "unknown"
        v = version.strip()
        if v.startswith("v") and len(v) > 1 and v[1].isdigit():
            v = v[1:]
        return v
