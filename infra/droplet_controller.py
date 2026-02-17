"""DigitalOcean droplet lifecycle management."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import digitalocean

if TYPE_CHECKING:
    from .os_matrix import OSTarget


@dataclass
class DropletConfig:
    """Configuration for creating a droplet."""
    
    name: str
    image: str
    region: str = "nyc3"
    size: str = "s-1vcpu-1gb"
    ssh_keys: list[str] | None = None
    tags: list[str] | None = None
    user_data: str | None = None


class DropletController:
    """Manages DigitalOcean droplet lifecycle."""
    
    def __init__(self, token: str | None = None) -> None:
        """Initialize controller.
        
        Args:
            token: DigitalOcean API token (or from DIGITALOCEAN_TOKEN env)
        """
        self.token = token or os.getenv("DIGITALOCEAN_TOKEN")
        if not self.token:
            raise ValueError("DigitalOcean token required")
        
        self.manager = digitalocean.Manager(token=self.token)
        self._tracked_droplets: list[digitalocean.Droplet] = []
    
    def create(
        self,
        config: DropletConfig,
        wait: bool = True,
        timeout: int = 300,
    ) -> digitalocean.Droplet:
        """Create a new droplet.
        
        Args:
            config: Droplet configuration
            wait: Whether to wait for droplet to be active
            timeout: Timeout in seconds
        
        Returns:
            Created droplet
        """
        droplet = digitalocean.Droplet(
            token=self.token,
            name=config.name,
            region=config.region,
            image=config.image,
            size_slug=config.size,
            ssh_keys=config.ssh_keys or [],
            tags=config.tags or ["sysadmin-ai-next-test"],
            user_data=config.user_data,
        )
        
        droplet.create()
        self._tracked_droplets.append(droplet)
        
        if wait:
            self._wait_for_active(droplet, timeout)
        
        return droplet
    
    def _wait_for_active(
        self,
        droplet: digitalocean.Droplet,
        timeout: int = 300,
    ) -> None:
        """Wait for droplet to become active."""
        start = time.time()
        while time.time() - start < timeout:
            droplet.load()
            if droplet.status == "active":
                return
            time.sleep(5)
        raise TimeoutError(f"Droplet {droplet.name} did not become active")
    
    def destroy(self, droplet: digitalocean.Droplet | str) -> None:
        """Destroy a droplet."""
        if isinstance(droplet, str):
            droplets = self.manager.get_all_droplets()
            for d in droplets:
                if d.name == droplet or str(d.id) == droplet:
                    droplet = d
                    break
            else:
                return
        
        droplet.destroy()
        if droplet in self._tracked_droplets:
            self._tracked_droplets.remove(droplet)
    
    def destroy_all(self, tag: str = "sysadmin-ai-next-test") -> int:
        """Destroy all droplets with given tag.
        
        Returns:
            Number of droplets destroyed
        """
        droplets = self.manager.get_all_droplets(tag_name=tag)
        count = 0
        for droplet in droplets:
            droplet.destroy()
            count += 1
        return count
    
    def get_droplet(self, droplet_id: int) -> digitalocean.Droplet:
        """Get droplet by ID."""
        return self.manager.get_droplet(droplet_id)
    
    def list_by_tag(self, tag: str = "sysadmin-ai-next-test") -> list[digitalocean.Droplet]:
        """List droplets by tag."""
        return self.manager.get_all_droplets(tag_name=tag)
    
    def get_or_create_ssh_key(self, public_key: str, name: str = "sysadmin-ai-next-key") -> digitalocean.SSHKey:
        """Get existing or upload new SSH key."""
        keys = self.manager.get_all_sshkeys()
        for key in keys:
            if key.public_key == public_key or key.name == name:
                return key
        
        key = digitalocean.SSHKey(
            token=self.token,
            name=name,
            public_key=public_key,
        )
        key.create()
        return key
    
    def cleanup(self) -> None:
        """Clean up all tracked droplets."""
        for droplet in list(self._tracked_droplets):
            try:
                droplet.destroy()
            except Exception:
                pass
        self._tracked_droplets.clear()
