"""SSH driver for remote command execution and file transfer."""

from __future__ import annotations

import io
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import paramiko

if TYPE_CHECKING:
    from .droplet_controller import digitalocean


class SSHDriver:
    """SSH connection manager for remote VMs."""
    
    def __init__(
        self,
        hostname: str,
        username: str = "root",
        key_path: str | None = None,
        key_content: str | None = None,
    ) -> None:
        """Initialize SSH driver.
        
        Args:
            hostname: IP or hostname
            username: SSH username
            key_path: Path to private key file
            key_content: Private key content (alternative to key_path)
        """
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.key_content = key_content
        self._client: paramiko.SSHClient | None = None
    
    def connect(self, timeout: int = 60, retries: int = 12) -> None:
        """Connect with retry logic.
        
        Args:
            timeout: Connection timeout per attempt
            retries: Number of retry attempts
        """
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        pkey = None
        if self.key_content:
            pkey = paramiko.RSAKey.from_private_key(io.StringIO(self.key_content))
        elif self.key_path:
            pkey = paramiko.RSAKey.from_private_key_file(self.key_path)
        
        for attempt in range(retries):
            try:
                self._client.connect(
                    hostname=self.hostname,
                    username=self.username,
                    pkey=pkey,
                    timeout=timeout,
                    banner_timeout=60,
                )
                return
            except (paramiko.SSHException, TimeoutError) as e:
                if attempt == retries - 1:
                    raise ConnectionError(f"Failed to connect after {retries} attempts: {e}")
                time.sleep(5)
    
    def exec(
        self,
        command: str,
        timeout: int = 60,
        sudo: bool = False,
    ) -> dict[str, Any]:
        """Execute a command on the remote host.
        
        Args:
            command: Command to execute
            timeout: Command timeout
            sudo: Run with sudo
        
        Returns:
            Dict with stdout, stderr, exit_code
        """
        if not self._client:
            raise RuntimeError("Not connected")
        
        if sudo:
            command = f"sudo {command}"
        
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        
        exit_code = stdout.channel.recv_exit_status()
        
        return {
            "stdout": stdout.read().decode("utf-8", errors="replace"),
            "stderr": stderr.read().decode("utf-8", errors="replace"),
            "exit_code": exit_code,
        }
    
    def upload(
        self,
        local_path: str | Path,
        remote_path: str,
    ) -> None:
        """Upload a file to the remote host."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        sftp = self._client.open_sftp()
        try:
            sftp.put(str(local_path), remote_path)
        finally:
            sftp.close()
    
    def upload_content(
        self,
        content: str,
        remote_path: str,
    ) -> None:
        """Upload string content to a remote file."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        sftp = self._client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as f:
                f.write(content)
        finally:
            sftp.close()
    
    def download(
        self,
        remote_path: str,
        local_path: str | Path,
    ) -> None:
        """Download a file from the remote host."""
        if not self._client:
            raise RuntimeError("Not connected")
        
        sftp = self._client.open_sftp()
        try:
            sftp.get(remote_path, str(local_path))
        finally:
            sftp.close()
    
    def close(self) -> None:
        """Close the SSH connection."""
        if self._client:
            self._client.close()
            self._client = None
    
    def __enter__(self) -> "SSHDriver":
        self.connect()
        return self
    
    def __exit__(self, *args: Any) -> None:
        self.close()
