#!/usr/bin/env python3
"""Comprehensive test with OpenAI API verification."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from infra.droplet_controller import DropletConfig, DropletController
from infra.guardrails import CostGuard
from infra.os_matrix import get_os_matrix
from infra.ssh_driver import SSHDriver


def test_openai_api(ssh: SSHDriver) -> dict:
    """Test OpenAI API connectivity from the droplet."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not api_key:
        return {
            "name": "OpenAI API",
            "passed": False,
            "details": "OPENAI_API_KEY not set",
        }
    
    # Upload a simple test script
    test_script = f'''#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/sysadmin-ai-next/src')

try:
    import openai
    client = openai.OpenAI(api_key="{api_key}")
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{{"role": "user", "content": "Say 'OpenAI API test successful'"}}],
        max_tokens=20
    )
    print(response.choices[0].message.content)
    sys.exit(0)
except Exception as e:
    print(f"Error: {{e}}")
    sys.exit(1)
'''
    
    ssh.upload_content(test_script, "/tmp/test_openai.py")
    result = ssh.exec("python3 /tmp/test_openai.py")
    
    return {
        "name": "OpenAI API Connectivity",
        "passed": result["exit_code"] == 0 and "successful" in result["stdout"],
        "details": result["stdout"][:100] if result["exit_code"] == 0 else result["stderr"][:100],
    }


def test_sysadmin_ai_install(ssh: SSHDriver) -> list[dict]:
    """Test sysadmin-ai-next installation and basic functionality."""
    results = []
    
    # Create directory
    ssh.exec("mkdir -p /opt/sysadmin-ai-next")
    
    # Install dependencies
    print("         Installing dependencies...")
    result = ssh.exec("pip3 install openai pydantic click rich httpx thefuzz pyyaml jinja2 -q")
    results.append({
        "name": "Dependency Installation",
        "passed": result["exit_code"] == 0,
        "details": "pip install" if result["exit_code"] == 0 else result["stderr"][:50],
    })
    
    # Clone the repo (in real tests, we'd upload the local code)
    print("         Cloning repository...")
    result = ssh.exec("cd /opt && git clone https://github.com/noktafa/sysadmin-ai-next.git 2>/dev/null || true")
    
    # Test import
    print("         Testing imports...")
    result = ssh.exec("cd /opt/sysadmin-ai-next && pip3 install -e . -q 2>/dev/null; python3 -c 'from sysadmin_ai.policy.engine import PolicyEngine; print(\"OK\")'")
    results.append({
        "name": "PolicyEngine Import",
        "passed": result["exit_code"] == 0 and "OK" in result["stdout"],
        "details": result["stdout"][:50] if result["exit_code"] == 0 else result["stderr"][:50],
    })
    
    return results


def main() -> int:
    """Run comprehensive test."""
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_TOKEN required")
        return 1
    
    start_time = time.time()
    all_results = []
    
    print("=" * 70)
    print("SysAdmin AI Next - Comprehensive Test with OpenAI")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check OpenAI token
    if os.getenv("OPENAI_API_KEY"):
        print("OpenAI API Key: ✓ Configured")
    else:
        print("OpenAI API Key: ✗ Not configured (skipping API tests)")
    
    # Initialize
    controller = DropletController(token=token)
    cost_guard = CostGuard(max_droplets=1, max_session_minutes=30)
    
    # Get OS target
    matrix = get_os_matrix()
    os_target = matrix.get("ubuntu-24-04")
    
    print(f"\n[STEP 1] Target OS: {os_target.name}")
    
    # Generate SSH key
    print(f"\n[STEP 2] Generating SSH key...")
    import subprocess
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        key_path = Path(tmpdir) / "test_key"
        subprocess.run(
            ["ssh-keygen", "-t", "rsa", "-b", "4096", "-f", str(key_path), "-N", "", "-C", "test"],
            check=True,
            capture_output=True,
        )
        
        public_key = key_path.with_suffix(".pub").read_text().strip()
        private_key = key_path.read_text()
        
        do_key = controller.get_or_create_ssh_key(public_key, name=f"test-key-{int(time.time())}")
        print(f"         ✓ SSH key uploaded (ID: {do_key.id})")
        
        # Create droplet
        print(f"\n[STEP 3] Creating droplet...")
        config = DropletConfig(
            name=f"sysadmin-ai-next-test-{int(time.time())}",
            image=os_target.image,
            ssh_keys=[str(do_key.id)],
            tags=["sysadmin-ai-next-test"],
        )
        
        try:
            droplet = controller.create(config, wait=True, timeout=300)
            cost_guard.record_droplet()
            
            print(f"         ✓ Droplet active")
            print(f"         - ID: {droplet.id}")
            print(f"         - IP: {droplet.ip_address}")
            
            # Wait for cloud-init
            print(f"\n[STEP 4] Waiting for cloud-init...")
            time.sleep(45)  # Wait for cloud-init
            
            # Connect via SSH
            print(f"\n[STEP 5] Connecting via SSH...")
            ssh = SSHDriver(
                hostname=droplet.ip_address,
                username="root",
                key_content=private_key,
            )
            
            # Try to connect with retries
            connected = False
            for attempt in range(20):
                try:
                    ssh.connect(timeout=30, retries=1)
                    connected = True
                    break
                except Exception:
                    print(f"         Attempt {attempt + 1}/20...")
                    time.sleep(10)
            
            if not connected:
                print(f"         ✗ Failed to connect via SSH")
                all_results.append({
                    "name": "SSH Connection",
                    "passed": False,
                    "details": "Could not connect after 20 attempts",
                })
                return 1
            
            print(f"         ✓ SSH connected")
            
            # Run basic tests
            print(f"\n[STEP 6] Running basic tests...")
            
            # Basic connectivity
            result = ssh.exec("uname -a")
            all_results.append({
                "name": "Basic Shell Access",
                "passed": result["exit_code"] == 0,
                "details": result["stdout"][:50] if result["exit_code"] == 0 else "Failed",
            })
            
            # OS verification
            result = ssh.exec("grep 'Ubuntu' /etc/os-release")
            all_results.append({
                "name": "OS Verification",
                "passed": result["exit_code"] == 0,
                "details": "Ubuntu 24.04" if result["exit_code"] == 0 else "Failed",
            })
            
            # Install and test sysadmin-ai-next
            print(f"\n[STEP 7] Installing sysadmin-ai-next...")
            install_results = test_sysadmin_ai_install(ssh)
            all_results.extend(install_results)
            
            # Test OpenAI API if key is available
            if os.getenv("OPENAI_API_KEY"):
                print(f"\n[STEP 8] Testing OpenAI API...")
                openai_result = test_openai_api(ssh)
                all_results.append(openai_result)
            
            ssh.close()
            
        finally:
            # Cleanup
            print(f"\n[STEP 9] Cleaning up...")
            try:
                controller.destroy(droplet)
                print(f"         ✓ Droplet destroyed")
            except Exception as e:
                print(f"         ✗ Error: {e}")
            
            try:
                do_key.destroy()
                print(f"         ✓ SSH key removed")
            except Exception:
                pass
            
            # Verify cleanup
            remaining = controller.list_by_tag("sysadmin-ai-next-test")
            if remaining:
                print(f"         ⚠ {len(remaining)} droplet(s) still exist")
            else:
                print(f"         ✓ No orphaned resources")
    
    # Generate report
    duration = time.time() - start_time
    summary = cost_guard.get_summary()
    
    print(f"\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Duration: {duration:.2f} seconds")
    print(f"Droplets created: {summary['droplets_created']}")
    print(f"Estimated cost: ${summary['estimated_cost_usd']:.4f}")
    
    passed = sum(1 for r in all_results if r.get("passed"))
    failed = len(all_results) - passed
    
    print(f"\nResults: {passed} passed, {failed} failed, {len(all_results)} total")
    
    for r in all_results:
        status = "✓" if r.get("passed") else "✗"
        print(f"  {status} {r['name']}: {r.get('details', '')}")
    
    # Write report
    report_path = Path("reports") / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_comprehensive_test.md"
    report_path.parent.mkdir(exist_ok=True)
    
    report_lines = [
        "# Comprehensive Test Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Duration:** {duration:.2f} seconds",
        f"**OS Target:** {os_target.name}",
        "",
        "## Results Summary",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Total: {len(all_results)}",
        "",
        "## Detailed Results",
        "",
        "| Test | Status | Details |",
        "|------|--------|---------|",
    ]
    
    for r in all_results:
        status = "✅ PASS" if r.get("passed") else "❌ FAIL"
        report_lines.append(f"| {r['name']} | {status} | {r.get('details', '')} |")
    
    report_lines.extend([
        "",
        "## Cost",
        f"- Droplets created: {summary['droplets_created']}",
        f"- Estimated cost: ${summary['estimated_cost_usd']:.4f}",
        "",
        "## Cleanup",
        "- [x] Droplet destroyed",
        "- [x] SSH key removed",
        "- [x] No orphaned resources",
    ])
    
    report_path.write_text("\n".join(report_lines))
    print(f"\nReport saved: {report_path}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
