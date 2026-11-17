"""Integration tests for project manifest parsers."""

from pathlib import Path

from inv.discovery.manifests import (
    parse_cargo_toml,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
)


def test_parse_package_json(temp_dir: Path) -> None:
    pkg_file = temp_dir / "package.json"
    pkg_file.write_text(
        """
        {
          "name": "my-node-app",
          "dependencies": {
            "react": "^18.2.0",
            "lodash": "4.17.21"
          },
          "devDependencies": {
            "typescript": "^5.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    deps = parse_package_json(pkg_file)
    assert len(deps) == 3
    dep_names = {d.name: d for d in deps}
    assert "react" in dep_names
    assert dep_names["react"].is_dev is False
    assert dep_names["typescript"].is_dev is True


def test_parse_pyproject_toml(temp_dir: Path) -> None:
    pyproj = temp_dir / "pyproject.toml"
    pyproj.write_text(
        """
        [project]
        name = "my-python-app"
        dependencies = [
            "typer>=0.9.0",
            "rich>=13.5.0",
        ]

        [project.optional-dependencies]
        dev = [
            "pytest>=7.0.0",
        ]
        """,
        encoding="utf-8",
    )
    deps = parse_pyproject_toml(pyproj)
    assert len(deps) == 3
    dep_names = {d.name: d for d in deps}
    assert "typer" in dep_names
    assert "pytest" in dep_names
    assert dep_names["pytest"].is_dev is True


def test_parse_requirements_txt(temp_dir: Path) -> None:
    req_file = temp_dir / "requirements.txt"
    req_file.write_text(
        """
        # Core requirements
        fastapi==0.109.0
        uvicorn[standard]>=0.27.0
        # Comment line
        requests>=2.31.0
        """,
        encoding="utf-8",
    )
    deps = parse_requirements_txt(req_file)
    assert len(deps) == 3
    names = [d.name for d in deps]
    assert "fastapi" in names
    assert "uvicorn" in names
    assert "requests" in names


def test_parse_cargo_toml(temp_dir: Path) -> None:
    cargo_file = temp_dir / "Cargo.toml"
    cargo_file.write_text(
        """
        [package]
        name = "my_rust_crate"
        version = "0.1.0"

        [dependencies]
        serde = "1.0"
        tokio = { version = "1.0", features = ["full"] }

        [dev-dependencies]
        tempfile = "3.8"
        """,
        encoding="utf-8",
    )
    deps = parse_cargo_toml(cargo_file)
    assert len(deps) == 3
    dep_names = {d.name: d for d in deps}
    assert "serde" in dep_names
    assert "tokio" in dep_names
    assert dep_names["tempfile"].is_dev is True


def test_parse_go_mod(temp_dir: Path) -> None:
    go_file = temp_dir / "go.mod"
    go_file.write_text(
        """
        module example.com/mygoapp

        go 1.21

        require (
            github.com/gin-gonic/gin v1.9.1
            github.com/stretchr/testify v1.8.4
        )
        """,
        encoding="utf-8",
    )
    deps = parse_go_mod(go_file)
    assert len(deps) == 2
    assert deps[0].name == "github.com/gin-gonic/gin"
    assert deps[0].resolved_version == "v1.9.1"
