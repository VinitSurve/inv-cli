"""Controlled executable version-probe registry.

Security Requirement:
Never execute arbitrary discovered binaries with arbitrary arguments.
Only binaries explicitly listed in this registry with safe, controlled arguments
may have their version probed at runtime.
"""

from pathlib import Path

from inv.constants import PROBE_PROCESS_TIMEOUT
from inv.utils.process import run_command
from inv.utils.versions import extract_version

# Controlled mapping of binary command name to safe argument list
PROBE_ARGUMENTS_MAP: dict[str, list[str]] = {
    # Languages & Runtimes
    "python": ["--version"],
    "python3": ["--version"],
    "python3.11": ["--version"],
    "python3.12": ["--version"],
    "python3.13": ["--version"],
    "python3.14": ["--version"],
    "python3.15": ["--version"],
    "python3.16": ["--version"],
    "pypy": ["--version"],
    "pypy3": ["--version"],
    "node": ["--version"],
    "deno": ["--version"],
    "bun": ["--version"],
    "ruby": ["--version"],
    "perl": ["--version"],
    "php": ["--version"],
    "rustc": ["--version"],
    "cargo": ["--version"],
    "rustup": ["--version"],
    "go": ["version"],
    "java": ["--version"],
    "javac": ["--version"],
    "swift": ["--version"],
    "elixir": ["--version"],
    "erl": ["+V"],
    "dotnet": ["--version"],
    "lua": ["-v"],
    # Package Managers & CLI tools
    "brew": ["--version"],
    "npm": ["--version"],
    "pnpm": ["--version"],
    "yarn": ["--version"],
    "pip": ["--version"],
    "pip3": ["--version"],
    "uv": ["--version"],
    "conda": ["--version"],
    "gem": ["--version"],
    "composer": ["--version"],
    # Developer utilities
    "git": ["--version"],
    "rg": ["--version"],
    "ripgrep": ["--version"],
    "fd": ["--version"],
    "fzf": ["--version"],
    "jq": ["--version"],
    "yq": ["--version"],
    "curl": ["--version"],
    "wget": ["--version"],
    "tar": ["--version"],
    "zip": ["-v"],
    "make": ["--version"],
    "cmake": ["--version"],
    "ninja": ["--version"],
    "ffmpeg": ["-version"],
    "sqlite3": ["--version"],
    "tmux": ["-V"],
    "vim": ["--version"],
    "nvim": ["--version"],
    "docker": ["--version"],
    "podman": ["--version"],
    "kubectl": ["version", "--client"],
    "zsh": ["--version"],
    "bash": ["--version"],
}


def can_probe_version(name: str) -> bool:
    """Check if binary name exists in safe version probe registry."""
    clean_name = name.lower()
    return clean_name in PROBE_ARGUMENTS_MAP


def probe_executable_version(name: str, path: Path) -> str | None:
    """Safely probe version of a known registered executable.

    Enforces:
    - Never probes unknown binaries.
    - Uses only predefined argument lists.
    - Strict timeout.
    """
    clean_name = name.lower()
    args = PROBE_ARGUMENTS_MAP.get(clean_name)
    if not args:
        return None

    try:
        cmd = [str(path), *args]
        res = run_command(cmd, timeout=PROBE_PROCESS_TIMEOUT)
        if res.timed_out:
            return None

        output = res.stdout if res.stdout else res.stderr
        return extract_version(output)
    except Exception:
        return None
