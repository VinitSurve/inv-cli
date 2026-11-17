"""Docker containers and images scanner with daemon accessibility checks."""

import json

from inv.constants import ScannerStatus
from inv.core.models import Container, ContainerImage
from inv.scanners.base import BaseScanner, ScanContext, ScanResult
from inv.utils.process import find_executable, run_command


class DockerScanner(BaseScanner):
    """Scanner for Docker containers and local images."""

    @property
    def scanner_id(self) -> str:
        return "docker"

    @property
    def domain(self) -> str:
        return "containers"

    @property
    def name(self) -> str:
        return "Docker Containers & Images"

    def is_available(self) -> bool:
        return find_executable("docker") is not None

    def scan(self, context: ScanContext) -> ScanResult:
        docker_bin = find_executable("docker") or "docker"
        result = ScanResult(scanner_id=self.scanner_id, domain=self.domain)

        # Quick probe to test if Docker daemon is responsive
        probe_res = run_command([docker_bin, "info"], timeout=3.0)
        if not probe_res.success:
            result.status = ScannerStatus.UNAVAILABLE
            result.warnings.append(
                "Docker binary is present, but daemon is not running or socket is inaccessible."
            )
            return result

        # 1. Containers: docker ps -a --format '{{json .}}'
        ps_res = run_command(
            [docker_bin, "ps", "-a", "--format", "{{json .}}"],
            timeout=context.config.process_timeout,
        )
        if ps_res.success:
            for line in ps_res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    c_data = json.loads(line)
                    c_id = c_data.get("ID") or c_data.get("ContainerID", "")
                    name = c_data.get("Names", "")
                    img = c_data.get("Image", "")
                    status = c_data.get("Status", "")
                    created = c_data.get("CreatedAt")
                    ports_str = c_data.get("Ports", "")
                    ports = [p.strip() for p in ports_str.split(",") if p.strip()]

                    container = Container.create(
                        container_id=c_id,
                        name=name,
                        image=img,
                        status=status,
                        created_at=created,
                        ports=ports,
                    )
                    result.containers.append(container)
                except Exception:
                    continue

        # 2. Images: docker images --format '{{json .}}'
        img_res = run_command(
            [docker_bin, "images", "--format", "{{json .}}"], timeout=context.config.process_timeout
        )
        if img_res.success:
            for line in img_res.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    i_data = json.loads(line)
                    img_id = i_data.get("ID", "")
                    repo = i_data.get("Repository", "")
                    tag = i_data.get("Tag", "")
                    created = i_data.get("CreatedAt")

                    image_obj = ContainerImage.create(
                        image_id=img_id,
                        repository=repo,
                        tag=tag,
                        created_at=created,
                    )
                    result.container_images.append(image_obj)
                except Exception:
                    continue

        return result
