#!/usr/bin/env python3
"""Quick test to verify environment works end-to-end."""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

sys.path.insert(0, str(Path(__file__).parent))

from infra.droplet_controller import DropletConfig, DropletController
from infra.guardrails import CostGuard
from infra.os_matrix import get_os_matrix


def main() -> int:
    """Run quick verification."""
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_TOKEN required", flush=True)
        return 1
    
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"OpenAI API Key: {'✓ Configured' if openai_key else '✗ Not configured'}", flush=True)
    
    start_time = time.time()
    print("\n" + "=" * 70, flush=True)
    print("Quick Environment Verification", flush=True)
    print("=" * 70, flush=True)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", flush=True)
    
    controller = DropletController(token=token)
    cost_guard = CostGuard(max_droplets=1, max_session_minutes=10)
    
    matrix = get_os_matrix()
    os_target = matrix.get("ubuntu-24-04")
    
    print(f"[1/4] Creating droplet on {os_target.name}...", flush=True)
    
    config = DropletConfig(
        name=f"quick-test-{int(time.time())}",
        image=os_target.image,
        tags=["sysadmin-ai-next-test"],
    )
    
    try:
        droplet = controller.create(config, wait=True, timeout=180)
        cost_guard.record_droplet()
        print(f"      ✓ Created: {droplet.name} ({droplet.ip_address})", flush=True)
        
        print(f"[2/4] Waiting 60s for cloud-init...", flush=True)
        time.sleep(60)
        print(f"      ✓ Wait complete", flush=True)
        
        print(f"[3/4] Testing connectivity...", flush=True)
        import subprocess
        ping = subprocess.run(
            ["ping", "-c", "2", "-W", "5", droplet.ip_address],
            capture_output=True,
        )
        if ping.returncode == 0:
            print(f"      ✓ Ping successful", flush=True)
        else:
            print(f"      ⚠ Ping failed", flush=True)
        
        print(f"[4/4] Cleaning up...", flush=True)
        
    except Exception as e:
        print(f"      ✗ Error: {e}", flush=True)
        return 1
    
    finally:
        try:
            controller.destroy(droplet)
            print(f"      ✓ Droplet destroyed", flush=True)
        except Exception as e:
            print(f"      ✗ Cleanup error: {e}", flush=True)
        
        # Verify
        remaining = controller.list_by_tag("sysadmin-ai-next-test")
        if remaining:
            print(f"      ⚠ {len(remaining)} droplet(s) remaining", flush=True)
        else:
            print(f"      ✓ No orphaned resources", flush=True)
    
    duration = time.time() - start_time
    summary = cost_guard.get_summary()
    
    print(f"\n" + "=" * 70, flush=True)
    print(f"Complete in {duration:.1f}s", flush=True)
    print(f"Cost: ${summary['estimated_cost_usd']:.4f}", flush=True)
    print("=" * 70, flush=True)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
