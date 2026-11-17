"""Confirmation and safety policy enforcement for package modification operations."""

import os
import sys

from inv.constants import OperationState
from inv.lifecycle.models import LifecycleOperation


class ModificationRefusedError(Exception):
    """Raised when an operation is refused due to policy, environment, or user decline."""


def is_interactive() -> bool:
    """Check if the current process is running in an interactive terminal."""
    # Allow test override via environment variable INV_FORCE_INTERACTIVE
    if os.environ.get("INV_FORCE_INTERACTIVE") == "1":
        return True
    return sys.stdin.isatty() and sys.stdout.isatty()


def request_operation_approval(
    operation: LifecycleOperation,
    prompt_text: str | None = None,
) -> bool:
    """Enforce explicit user confirmation for a planned lifecycle operation.

    Policy:
    - Non-interactive environments are refused by default.
    - Default confirmation answer is strictly NO.
    - Only explicit 'y' or 'yes' confirms.
    """
    if operation.status != OperationState.PLANNED:
        raise ModificationRefusedError(
            f"Cannot approve operation {operation.id} in state '{operation.status.value}'. Must be 'planned'."
        )

    # Check non-interactive terminal refusal policy
    if not is_interactive():
        # Check if authorized test token is present
        auth_token = os.environ.get("INV_AUTHORIZED_NON_INTERACTIVE_TOKEN")
        if not auth_token or auth_token != operation.id:
            operation.status = OperationState.CANCELLED
            raise ModificationRefusedError(
                "Package modification refused in non-interactive environment. "
                "All installations, removals, and upgrades require explicit interactive confirmation."
            )

    # In interactive environment, request explicit confirmation
    prompt = prompt_text or "Confirm this exact operation? [y/N]: "
    try:
        response = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        operation.status = OperationState.CANCELLED
        return False

    if response in ("y", "yes"):
        return True

    operation.status = OperationState.CANCELLED
    return False
