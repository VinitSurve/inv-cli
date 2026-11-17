"""Registry and manager resolution for lifecycle adapters."""

from inv.adapters.base import BaseLifecycleAdapter
from inv.adapters.bun import BunAdapter
from inv.adapters.cargo import CargoAdapter
from inv.adapters.homebrew import HomebrewAdapter
from inv.adapters.npm import NpmAdapter
from inv.adapters.pip import PipAdapter
from inv.adapters.pnpm import PnpmAdapter
from inv.adapters.unsupported import ReadOnlyLifecycleAdapter
from inv.adapters.uv import UvAdapter
from inv.adapters.yarn import YarnAdapter
from inv.storage.repositories import InventoryRepository


class LifecycleRegistry:
    """Registry maintaining active package manager lifecycle adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseLifecycleAdapter] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register supported and read-only manager adapters."""
        # Supported modification adapters
        self.register(HomebrewAdapter(is_cask=False))
        self.register(HomebrewAdapter(is_cask=True))
        self.register(NpmAdapter())
        self.register(PnpmAdapter())
        self.register(PipAdapter())
        self.register(UvAdapter())
        self.register(CargoAdapter())
        self.register(BunAdapter())
        self.register(YarnAdapter())

        # Read-only / discovery-only adapters
        self.register(ReadOnlyLifecycleAdapter("macports", "MacPorts", "port"))
        self.register(ReadOnlyLifecycleAdapter("gem", "RubyGems", "gem"))
        self.register(ReadOnlyLifecycleAdapter("composer", "PHP Composer", "composer"))
        self.register(ReadOnlyLifecycleAdapter("go", "Go Tools", "go"))
        self.register(ReadOnlyLifecycleAdapter("conda", "Conda", "conda"))

    def register(self, adapter: BaseLifecycleAdapter) -> None:
        """Register an adapter instance."""
        self._adapters[adapter.manager_id] = adapter

    def get(self, manager_id: str) -> BaseLifecycleAdapter | None:
        """Retrieve adapter by manager ID."""
        norm = manager_id.strip().lower()
        if norm in ("brew", "homebrew", "brew_formula"):
            norm = "brew_formula"
        elif norm in ("cask", "brew_cask"):
            norm = "brew_cask"
        elif norm in ("uv", "uv-tool", "uv_tool"):
            norm = "uv_tool"
        elif norm in ("npm", "npm_global"):
            norm = "npm"
        elif norm in ("pnpm", "pnpm_global"):
            norm = "pnpm"
        elif norm in ("yarn", "yarn_global"):
            norm = "yarn"
        elif norm in ("bun", "bun_global"):
            norm = "bun"
        return self._adapters.get(norm)

    def list_all(self) -> list[BaseLifecycleAdapter]:
        """Return all registered adapters."""
        return list(self._adapters.values())

    def resolve_manager_for_package(
        self,
        package_name: str,
        explicit_manager: str | None = None,
        repo: InventoryRepository | None = None,
        session_id: str | None = None,
    ) -> BaseLifecycleAdapter:
        """Resolve the appropriate lifecycle adapter for a target package."""
        if explicit_manager:
            adapter = self.get(explicit_manager)
            if not adapter:
                raise ValueError(f"Unknown or unsupported package manager '{explicit_manager}'.")
            return adapter

        # If repo is provided, check if package is already installed
        candidates: list[BaseLifecycleAdapter] = []
        if repo:
            insts = repo.list_installations(session_id)
            matching_mgrs = {
                inst.manager for inst in insts if inst.name.lower() == package_name.lower()
            }
            for mgr in matching_mgrs:
                a = self.get(mgr)
                if a and a.is_available():
                    candidates.append(a)

        # If not found in installed inventory, find available candidate adapters
        if not candidates:
            for adapter in self.list_all():
                if adapter.is_available() and adapter.supported_capabilities:
                    # check if package info exists
                    try:
                        info = adapter.get_package_info(package_name)
                        if info:
                            candidates.append(adapter)
                    except Exception:
                        pass

        if not candidates:
            # Default to Homebrew formula if available
            brew = self.get("brew_formula")
            if brew and brew.is_available():
                return brew
            # Or first available supported adapter
            avail = [a for a in self.list_all() if a.is_available() and a.supported_capabilities]
            if avail:
                return avail[0]
            raise ValueError(
                f"No available package manager found on this system to manage '{package_name}'."
            )

        if len(candidates) > 1:
            candidate_names = [c.manager_id for c in candidates]
            raise ValueError(
                f"Ambiguous package manager for '{package_name}'. "
                f"Please specify explicitly using --manager <manager> (candidates: {', '.join(candidate_names)})."
            )

        return candidates[0]
