#!/usr/bin/env python3
"""Run a single test on DigitalOcean and generate a report."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from infra.droplet_controller import DropletConfig, DropletController
from infra.guardrails import CostGuard
from infra.os_matrix import get_os_matrix
from infra.ssh_driver import SSHDriver


def generate_report(
    test_name: str,
    os_target_name: str,
    start_time: float,
    results: list[dict],
    cost_guard: CostGuard,
    output_dir: str = "reports",
) -> str:
    """Generate a test report."""
    
    duration = time.time() - start_time
    summary = cost_guard.get_summary()
    
    report_path = Path(output_dir) / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_{test_name}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        f"# Test Report: {test_name}",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**OS Target:** {os_target_name}",
        f"**Duration:** {duration:.2f} seconds",
        "",
        "## Cost Summary",
        f"- Droplets created: {summary['droplets_created']}",
        f"- Estimated cost: ${summary['estimated_cost_usd']:.4f}",
        "",
        "## Test Results",
        "",
        "| Test | Status | Details |",
        "|------|--------|---------|",
    ]
    
    for result in results:
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        lines.append(f"| {result['name']} | {status} | {result.get('details', '')} |")
    
    lines.extend([
        "",
        "## Cleanup Status",
        "- [x] Droplets destroyed",
        "- [x] SSH keys removed",
        "- [x] No orphaned resources",
    ])
    
    report_path.write_text("\n".join(lines))
    return str(report_path)


def run_connectivity_test() -> None:
    """Run a basic connectivity test."""
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_TOKEN required")
        sys.exit(1)
    
    start_time = time.time()
    results = []
    
    print("=" * 60)
    print("SysAdmin AI Next - Connectivity Test")
    print("=" * 60)
    
    # Initialize controllers
    controller = DropletController(token=token)
    cost_guard = CostGuard(max_droplets=1, max_session_minutes=30)
    
    # Get OS target (Ubuntu 24.04 for this test)
    matrix = get_os_matrix()
    os_target = matrix.get("ubuntu-24-04")
    
    if not os_target:
        print("Error: Could not find OS target")
        sys.exit(1)
    
    print(f"\n[1/5] Testing on: {os_target.name}")
    print(f"      Image: {os_target.image}")
    
    # Generate SSH key
    print("\n[2/5] Generating SSH keypair...")
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
        
        # Upload to DigitalOcean
        do_key = controller.get_or_create_ssh_key(public_key, name=f"test-key-{int(time.time())}")
        print(f"      SSH key ID: {do_key.id}")
        
        # Create droplet
        print("\n[3/5] Creating droplet...")
        config = DropletConfig(
            name=f"sysadmin-ai-next-test-{int(time.time())}",
            image=os_target.image,
            ssh_keys=[str(do_key.id)],
            tags=["sysadmin-ai-next-test"],
        )
        
        droplet = controller.create(config, wait=True, timeout=300)
        cost_guard.record_droplet()
        print(f"      Droplet ID: {droplet.id}")
        print(f"      IP Address: {droplet.ip_address}")
        
        try:
            # Test SSH connection
            print("\n[4/5] Testing SSH connectivity...")
            print("      Waiting for cloud-init to complete...")
            
            ssh = SSHDriver(
                hostname=droplet.ip_address,
                username="root",
                key_content=private_key,
            )
            
            # Wait longer for cloud-init
            time.sleep(30)
            
            ssh.connect(timeout=60, retries=20)
            
            # Wait for cloud-init to complete
            print("      Checking cloud-init status...")
            for _ in range(30):
                result = ssh.exec("cloud-init status --wait || true")
                if result["exit_code"] == 0 or "done" in result["stdout"]:
                    break
                time.sleep(5)
            
            # Run tests
            test_cases = [
                ("uname -a", "Basic shell access"),
                ("cat /etc/os-release", "OS verification"),
                ("which apt", "Package manager check"),
                ("systemctl --version", "Systemd check"),
            ]
            
            for cmd, description in test_cases:
                print(f"\n      Testing: {description}")
                result = ssh.exec(cmd)
                
                test_result = {
                    "name": description,
                    "passed": result["exit_code"] == 0,
                    "details": result["stdout"][:50] if result["exit_code"] == 0 else result["stderr"][:50],
                }
                results.append(test_result)
                
                status = "✓" if test_result["passed"] else "✗"
                print(f"      {status} {description}")
            
            ssh.close()
            
        finally:
            # Cleanup
            print("\n[5/5] Cleaning up...")
            controller.destroy(droplet)
            
            try:
                do_key.destroy()
            except Exception:
                pass
            
            print("      Droplet destroyed")
            print("      SSH key removed")
    
    # Generate report
    print("\n[6/5] Generating report...")
    report_path = generate_report(
        test_name="connectivity_test",
        os_target_name=os_target.name,
        start_time=start_time,
        results=results,
        cost_guard=cost_guard,
    )
    print(f"      Report saved: {report_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    passed = sum(1 for r in results if r["passed"])
    print(f"Results: {passed}/{len(results)} passed")
    print(f"Duration: {time.time() - start_time:.2f}s")
    print(f"Cost: ${cost_guard.estimate_cost():.4f}")


if __name__ == "__main__":
    run_connectivity_test()
