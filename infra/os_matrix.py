"""OS target definitions for test matrix."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OSTarget:
    """Represents an OS target for testing."""
    
    name: str
    image: str
    family: str  # debian or rhel
    package_manager: str  # apt or dnf
    setup_commands: list[str] | None = None


# Default OS matrix
DEFAULT_TARGETS = [
    OSTarget(
        name="ubuntu-24-04",
        image="ubuntu-24-04-x64",
        family="debian",
        package_manager="apt",
        setup_commands=[
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv",
        ],
    ),
    OSTarget(
        name="ubuntu-22-04",
        image="ubuntu-22-04-x64",
        family="debian",
        package_manager="apt",
        setup_commands=[
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv",
        ],
    ),
    OSTarget(
        name="debian-12",
        image="debian-12-x64",
        family="debian",
        package_manager="apt",
        setup_commands=[
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv",
        ],
    ),
    OSTarget(
        name="centos-stream-9",
        image="centos-stream-9-x64",
        family="rhel",
        package_manager="dnf",
        setup_commands=[
            "dnf install -y python3 python3-pip",
        ],
    ),
    OSTarget(
        name="fedora-42",
        image="fedora-42-x64",
        family="rhel",
        package_manager="dnf",
        setup_commands=[
            "dnf install -y python3 python3-pip",
        ],
    ),
    OSTarget(
        name="almalinux-9",
        image="almalinux-9-x64",
        family="rhel",
        package_manager="dnf",
        setup_commands=[
            "dnf install -y python3 python3-pip",
        ],
    ),
]


class OSMatrix:
    """Manages the OS test matrix."""
    
    def __init__(self, snapshot_file: str | Path | None = None) -> None:
        """Initialize OS matrix.
        
        Args:
            snapshot_file: Path to snapshots.json for pre-built images
        """
        self.targets = DEFAULT_TARGETS.copy()
        self._snapshots: dict[str, str] = {}
        
        if snapshot_file:
            self._load_snapshots(Path(snapshot_file))
    
    def _load_snapshots(self, path: Path) -> None:
        """Load snapshot IDs from file."""
        if path.exists():
            with open(path) as f:
                self._snapshots = json.load(f)
            
            # Apply snapshots to targets
            for target in self.targets:
                if target.name in self._snapshots:
                    target.image = self._snapshots[target.name]
    
    def get(self, name: str) -> OSTarget | None:
        """Get target by name."""
        for target in self.targets:
            if target.name == name:
                return target
        return None
    
    def get_all(self) -> list[OSTarget]:
        """Get all targets."""
        return self.targets
    
    def get_by_family(self, family: str) -> list[OSTarget]:
        """Get targets by family (debian/rhel)."""
        return [t for t in self.targets if t.family == family]
    
    def save_snapshots(self, path: str | Path) -> None:
        """Save current snapshot configuration."""
        with open(path, "w") as f:
            json.dump(self._snapshots, f, indent=2)


def get_os_matrix() -> OSMatrix:
    """Get configured OS matrix."""
    snapshot_file = os.getenv("SNAPSHOT_FILE", "infra/snapshots.json")
    return OSMatrix(snapshot_file=snapshot_file)
