"""Test runner script."""

#!/usr/bin/env python3
"""Cross-platform test runner for sysadmin-ai-next-tests."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_unit_tests(args: list[str]) -> int:
    """Run unit tests (fast, no cloud resources)."""
    cmd = ["pytest", "-xvs", "-m", "unit"] + args
    return subprocess.call(cmd)


def run_integration_tests(args: list[str]) -> int:
    """Run integration tests (requires DigitalOcean)."""
    # Check for token
    if not os.getenv("DIGITALOCEAN_TOKEN"):
        print("Error: DIGITALOCEAN_TOKEN environment variable required")
        return 1
    
    # Run with parallel workers (one per OS target)
    cmd = [
        "pytest",
        "tests/integration",
        "-xvs",
        "--dist", "loadgroup",
        "-n", "6",
    ] + args
    
    return subprocess.call(cmd)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run sysadmin-ai-next tests")
    parser.add_argument(
        "command",
        choices=["unit", "integration", "all"],
        help="Test suite to run",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional arguments to pass to pytest",
    )
    
    args = parser.parse_args()
    
    if args.command == "unit":
        return run_unit_tests(args.pytest_args)
    elif args.command == "integration":
        return run_integration_tests(args.pytest_args)
    elif args.command == "all":
        unit_code = run_unit_tests(args.pytest_args)
        if unit_code != 0:
            return unit_code
        return run_integration_tests(args.pytest_args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
