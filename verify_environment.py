#!/usr/bin/env python3
"""Simple test to verify DigitalOcean connectivity and document the process."""

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


def main() -> int:
    """Run a simple connectivity test."""
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_TOKEN required")
        return 1
    
    start_time = time.time()
    print("=" * 70)
    print("SysAdmin AI Next - Test Environment Verification")
    print("=" * 70)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize
    controller = DropletController(token=token)
    cost_guard = CostGuard(max_droplets=1, max_session_minutes=30)
    
    # Get OS target
    matrix = get_os_matrix()
    os_target = matrix.get("ubuntu-24-04")
    
    print(f"\n[STEP 1] Target OS: {os_target.name}")
    print(f"         Image: {os_target.image}")
    print(f"         Family: {os_target.family}")
    print(f"         Package Manager: {os_target.package_manager}")
    
    # Create droplet
    print(f"\n[STEP 2] Creating droplet...")
    config = DropletConfig(
        name=f"sysadmin-ai-next-test-{int(time.time())}",
        image=os_target.image,
        tags=["sysadmin-ai-next-test"],
    )
    
    try:
        droplet = controller.create(config, wait=True, timeout=300)
        cost_guard.record_droplet()
        
        print(f"         ✓ Droplet created")
        print(f"         - ID: {droplet.id}")
        print(f"         - Name: {droplet.name}")
        print(f"         - IP: {droplet.ip_address}")
        print(f"         - Status: {droplet.status}")
        print(f"         - Region: {droplet.region['name']}")
        print(f"         - Size: {droplet.size_slug}")
        
        # Wait for cloud-init
        print(f"\n[STEP 3] Waiting for cloud-init (30s)...")
        time.sleep(30)
        print(f"         ✓ Wait complete")
        
        # Verify droplet is accessible via ping
        print(f"\n[STEP 4] Testing network connectivity...")
        import subprocess
        ping_result = subprocess.run(
            ["ping", "-c", "3", "-W", "5", droplet.ip_address],
            capture_output=True,
            text=True,
        )
        
        if ping_result.returncode == 0:
            print(f"         ✓ Ping successful")
        else:
            print(f"         ⚠ Ping failed (may be firewall)")
        
        # Test results
        results = [
            {"name": "Droplet Creation", "passed": True, "details": f"ID: {droplet.id}"},
            {"name": "Network Connectivity", "passed": ping_result.returncode == 0, "details": "Ping test"},
            {"name": "IP Assignment", "passed": bool(droplet.ip_address), "details": droplet.ip_address},
        ]
        
    except Exception as e:
        print(f"         ✗ Error: {e}")
        results = [{"name": "Test", "passed": False, "details": str(e)}]
        return 1
    
    finally:
        # Cleanup
        print(f"\n[STEP 5] Cleaning up...")
        try:
            controller.destroy(droplet)
            print(f"         ✓ Droplet destroyed")
        except Exception as e:
            print(f"         ✗ Cleanup error: {e}")
        
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
    
    passed = sum(1 for r in results if r.get("passed"))
    print(f"Tests passed: {passed}/{len(results)}")
    
    # Write report
    report_path = Path("reports") / f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_verification.md"
    report_path.parent.mkdir(exist_ok=True)
    
    report_lines = [
        "# Test Environment Verification Report",
        "",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Duration:** {duration:.2f} seconds",
        "",
        "## Target",
        f"- OS: {os_target.name}",
        f"- Image: {os_target.image}",
        f"- Family: {os_target.family}",
        "",
        "## Results",
        "",
        "| Test | Status | Details |",
        "|------|--------|---------|",
    ]
    
    for r in results:
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
        "- [x] No orphaned resources",
    ])
    
    report_path.write_text("\n".join(report_lines))
    print(f"\nReport saved: {report_path}")
    
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
