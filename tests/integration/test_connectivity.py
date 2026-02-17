"""Basic connectivity tests."""

import pytest


@pytest.mark.dependency()
class TestConnectivity:
    """Test basic VM connectivity."""
    
    def test_ssh_access(self, ssh) -> None:
        """Test SSH connection works."""
        result = ssh.exec("uname -a")
        assert result["exit_code"] == 0
        assert "Linux" in result["stdout"]
    
    def test_os_family(self, ssh, os_target) -> None:
        """Test OS family matches expected."""
        result = ssh.exec("cat /etc/os-release")
        assert result["exit_code"] == 0
        
        if os_target.family == "debian":
            assert any(x in result["stdout"] for x in ["debian", "ubuntu"])
        elif os_target.family == "rhel":
            assert any(x in result["stdout"] for x in ["centos", "fedora", "almalinux", "rhel"])
    
    def test_package_manager(self, ssh, os_target) -> None:
        """Test package manager is available."""
        result = ssh.exec(f"which {os_target.package_manager}")
        assert result["exit_code"] == 0
    
    def test_systemd(self, ssh) -> None:
        """Test systemd is present."""
        result = ssh.exec("systemctl --version")
        assert result["exit_code"] == 0
