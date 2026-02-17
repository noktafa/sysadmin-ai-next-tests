#!/usr/bin/env python3
"""Emergency cleanup script for orphaned resources."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infra.droplet_controller import DropletController


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean up orphaned test resources")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List resources without destroying",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Destroy without confirmation",
    )
    
    args = parser.parse_args()
    
    token = os.getenv("DIGITALOCEAN_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_TOKEN required")
        return 1
    
    controller = DropletController(token=token)
    
    # Find orphaned droplets
    droplets = controller.list_by_tag("sysadmin-ai-next-test")
    
    if not droplets:
        print("No orphaned resources found")
        return 0
    
    print(f"Found {len(droplets)} orphaned droplet(s):")
    for d in droplets:
        print(f"  - {d.name} ({d.ip_address}, {d.status})")
    
    if args.dry_run:
        return 0
    
    if not args.force:
        confirm = input("\nDestroy these droplets? [y/N] ")
        if confirm.lower() != "y":
            print("Cancelled")
            return 0
    
    print("\nDestroying...")
    count = controller.destroy_all("sysadmin-ai-next-test")
    print(f"Destroyed {count} droplet(s)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
