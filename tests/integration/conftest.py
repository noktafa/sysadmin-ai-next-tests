"""Pytest fixtures and configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pytest

from infra.droplet_controller import DropletConfig, DropletController
from infra.guardrails import CostGuard, SessionGuard
from infra.os_matrix import get_os_matrix, OSTarget
from infra.ssh_driver import SSHDriver

if TYPE_CHECKING:
    import digitalocean


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom pytest options."""
    parser.addoption(
        "--skip-snapshots",
        action="store_true",
        default=False,
        help="Skip tests that require pre-built snapshots",
    )


@pytest.fixture(scope="session")
def do_token() -> str:
    """Get DigitalOcean token."""
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        pytest.skip("DIGITALOCEAN_TOKEN not set")
    return token


@pytest.fixture(scope="session")
def controller(do_token: str) -> Generator[DropletController, None, None]:
    """Session-scoped droplet controller."""
    ctrl = DropletController(token=do_token)
    guard = SessionGuard(ctrl)
    
    yield ctrl
    
    # Cleanup on session end
    print("\nCleaning up droplets...")
    guard.cleanup()


@pytest.fixture(scope="session")
def cost_guard() -> CostGuard:
    """Session cost guard."""
    return CostGuard()


@pytest.fixture(scope="session")
def ssh_key(controller: DropletController) -> Generator[tuple[str, str], None, None]:
    """Generate ephemeral SSH keypair."""
    import subprocess
    
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = Path(tmpdir) / "test_key"
        
        # Generate key
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(key_path), "-N", "", "-C", "sysadmin-ai-next-test"],
            check=True,
            capture_output=True,
        )
        
        public_key = key_path.with_suffix(".pub").read_text().strip()
        private_key = key_path.read_text()
        
        # Upload to DigitalOcean
        do_key = controller.get_or_create_ssh_key(public_key)
        
        yield private_key, do_key.id
        
        # Cleanup key
        try:
            do_key.destroy()
        except Exception:
            pass


@pytest.fixture(scope="function")
def os_target(request: pytest.FixtureRequest) -> OSTarget:
    """Get OS target for current test."""
    matrix = get_os_matrix()
    
    # Get target from test node marker or parameter
    target_name = getattr(request.node, "os_target", None)
    if not target_name:
        # Try to get from parameter
        if hasattr(request, "param"):
            target_name = request.param
        else:
            # Default to first target
            target_name = matrix.get_all()[0].name
    
    target = matrix.get(target_name)
    if not target:
        pytest.skip(f"Unknown OS target: {target_name}")
    
    return target


@pytest.fixture(scope="function")
def droplet(
    controller: DropletController,
    ssh_key: tuple[str, str],
    os_target: OSTarget,
    cost_guard: CostGuard,
) -> Generator[digitalocean.Droplet, None, None]:
    """Create a droplet for testing."""
    if not cost_guard.check_droplet_limit():
        pytest.skip("Droplet limit reached")
    
    if not cost_guard.check_timeout():
        pytest.skip("Session timeout reached")
    
    private_key, key_id = ssh_key
    
    config = DropletConfig(
        name=f"sysadmin-ai-next-test-{os_target.name}-{os.urandom(4).hex()}",
        image=os_target.image,
        ssh_keys=[str(key_id)],
        tags=["sysadmin-ai-next-test"],
    )
    
    droplet = controller.create(config, wait=True)
    cost_guard.record_droplet()
    
    yield droplet
    
    # Destroy droplet after test
    controller.destroy(droplet)


@pytest.fixture(scope="function")
def ssh(
    droplet: digitalocean.Droplet,
    ssh_key: tuple[str, str],
) -> Generator[SSHDriver, None, None]:
    """SSH connection to droplet."""
    private_key, _ = ssh_key
    
    driver = SSHDriver(
        hostname=droplet.ip_address,
        username="root",
        key_content=private_key,
    )
    
    driver.connect()
    yield driver
    driver.close()
