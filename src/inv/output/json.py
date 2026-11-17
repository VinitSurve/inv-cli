"""JSON exporter for inventory data."""

import json
from typing import Any

from inv.core.models import (
    Application,
    Container,
    Environment,
    ExecutableInstance,
    InstallationInstance,
    Project,
    ProjectDependency,
    Runtime,
    ScannerObservation,
    ScanSession,
)


def export_inventory_json(
    session: ScanSession | None,
    installations: list[InstallationInstance],
    executables: list[ExecutableInstance],
    applications: list[Application],
    projects: list[Project],
    dependencies: list[ProjectDependency],
    environments: list[Environment],
    runtimes: list[Runtime],
    containers: list[Container],
    observations: list[ScannerObservation],
) -> str:
    """Serialize entire inventory dataset to formatted JSON string."""
    payload: dict[str, Any] = {
        "session": session.to_dict() if session else None,
        "summary": session.summary if session else {},
        "installations": [i.to_dict() for i in installations],
        "executables": [e.to_dict() for e in executables],
        "applications": [a.to_dict() for a in applications],
        "projects": [p.to_dict() for p in projects],
        "dependencies": [d.to_dict() for d in dependencies],
        "environments": [e.to_dict() for e in environments],
        "runtimes": [r.to_dict() for r in runtimes],
        "containers": [c.to_dict() for c in containers],
        "observations": [o.to_dict() for o in observations],
    }
    return json.dumps(payload, indent=2)
