"""Sandbox isolation tests."""

import pytest


@pytest.mark.dependency(depends=["TestConnectivity"])
class TestSandbox:
    """Test sandbox isolation functionality."""
    
    def test_docker_available(self, ssh) -> None:
        """Test Docker is available on the VM."""
        result = ssh.exec("which docker")
        # Docker may not be installed by default
        if result["exit_code"] != 0:
            pytest.skip("Docker not available")
    
    def test_sandbox_creation(self, ssh) -> None:
        """Test creating a sandbox."""
        # This would test the SandboxManager once deployed
        pass
    
    def test_sandbox_isolation(self, ssh) -> None:
        """Test that sandbox provides isolation."""
        # Test that commands in sandbox don't affect host
        pass
    
    def test_sandbox_cleanup(self, ssh) -> None:
        """Test sandbox cleanup after use."""
        pass
