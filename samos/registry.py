"""Module registry for sam-os.

Discovers and loads modules from samos/modules/. Each module declares a
MODULE manifest with its tools, resources, migrations, and scheduler jobs.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import samos.modules


@dataclass
class Module:
    name: str
    display_name: str
    description: str
    required_env: list[str] = field(default_factory=list)
    optional_env: list[str] = field(default_factory=list)
    tools: list[Callable] = field(default_factory=list)
    resources: list[Callable] = field(default_factory=list)
    scheduler_jobs: list[dict] = field(default_factory=list)
    migrations_dir: Path | None = None
    enabled: bool = True
    disable_reason: str | None = None


class Registry:
    def __init__(self):
        self.modules: dict[str, Module] = {}
        self._discover()

    def _discover(self):
        for finder, name, ispkg in pkgutil.iter_modules(samos.modules.__path__):
            if not ispkg:
                continue
            try:
                mod = importlib.import_module(f"samos.modules.{name}")
                manifest = getattr(mod, "MODULE", None)
                if not manifest:
                    continue
                module = Module(
                    name=manifest.get("name", name),
                    display_name=manifest.get("display_name", name),
                    description=manifest.get("description", ""),
                    required_env=manifest.get("required_env", []),
                    optional_env=manifest.get("optional_env", []),
                    tools=manifest.get("tools", []),
                    resources=manifest.get("resources", []),
                    scheduler_jobs=manifest.get("scheduler_jobs", []),
                    migrations_dir=Path(samos.modules.__file__).parent / name / "migrations",
                )
                self.modules[module.name] = module
            except Exception as e:
                # Log but do not crash startup because of one bad module.
                print(f"[registry] failed to load module '{name}': {e}")

    def check_enabled(self):
        """Mark modules disabled if required env vars are missing."""
        import os

        for module in self.modules.values():
            missing = [k for k in module.required_env if not os.environ.get(k)]
            if missing:
                module.enabled = False
                module.disable_reason = f"missing required env: {', '.join(missing)}"

    def enabled_modules(self) -> list[Module]:
        return [m for m in self.modules.values() if m.enabled]

    def list_manifests(self) -> list[dict]:
        return [
            {
                "name": m.name,
                "display_name": m.display_name,
                "description": m.description,
                "enabled": m.enabled,
                "disable_reason": m.disable_reason,
                "required_env": m.required_env,
                "optional_env": m.optional_env,
                "tools": [t.__name__ for t in m.tools],
                "resources": [getattr(r, "_resource_name", r.__name__) for r in m.resources],
            }
            for m in self.modules.values()
        ]

    def all_tools(self) -> list[Callable]:
        tools = []
        for m in self.enabled_modules():
            tools.extend(m.tools)
        return tools

    def all_resources(self) -> list[Callable]:
        resources = []
        for m in self.enabled_modules():
            resources.extend(m.resources)
        return resources

    def all_scheduler_jobs(self) -> list[dict]:
        jobs = []
        for m in self.enabled_modules():
            jobs.extend(m.scheduler_jobs)
        return jobs

    def migration_dirs(self) -> list[Path]:
        dirs = []
        for m in self.enabled_modules():
            if m.migrations_dir and m.migrations_dir.exists():
                dirs.append(m.migrations_dir)
        return dirs


REGISTRY = Registry()
