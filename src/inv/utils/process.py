"""Safe subprocess execution helper."""

import shutil
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass

from inv.constants import DEFAULT_PROCESS_TIMEOUT
from inv.exceptions import ProcessExecutionError


@dataclass
class ProcessResult:
    """Represents the outcome of a subprocess execution."""

    argv: list[str]
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """True if execution completed with returncode 0."""
        return self.exit_code == 0 and not self.timed_out


def find_executable(name: str) -> str | None:
    """Find absolute path of an executable if present in system PATH."""
    return shutil.which(name)


def run_command(
    argv: Sequence[str],
    timeout: float = DEFAULT_PROCESS_TIMEOUT,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> ProcessResult:
    """Execute a command safely using an argv list.

    Enforces:
    - shell=False strictly
    - Strict timeout
    - Safe decoding with replacement for invalid utf-8 bytes
    - Exception handling for missing binaries or permission denial
    """
    if not argv:
        raise ValueError("argv cannot be empty")

    cmd_list = [str(arg) for arg in argv]

    try:
        proc = subprocess.run(
            cmd_list,
            shell=False,
            capture_output=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return ProcessResult(
            argv=cmd_list,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            timed_out=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout.decode("utf-8", "replace") if exc.stdout else "")
        )
        stderr = (
            exc.stderr
            if isinstance(exc.stderr, str)
            else (exc.stderr.decode("utf-8", "replace") if exc.stderr else "")
        )
        return ProcessResult(
            argv=cmd_list,
            exit_code=-1,
            stdout=stdout,
            stderr=f"Process timed out after {timeout} seconds: {stderr}",
            timed_out=True,
        )
    except (FileNotFoundError, PermissionError) as exc:
        return ProcessResult(
            argv=cmd_list,
            exit_code=-2,
            stdout="",
            stderr=f"Execution failed ({type(exc).__name__}): {exc}",
            timed_out=False,
        )
    except Exception as exc:
        raise ProcessExecutionError(f"Unexpected error running {cmd_list}: {exc}") from exc
