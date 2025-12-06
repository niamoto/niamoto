#!/usr/bin/env python
"""
Script to run tests with optimized performance.

This script runs the tests with optimized settings to improve performance.
"""

import os
import sys
import time
import subprocess
from pathlib import Path


def main():
    """Run tests with optimized settings."""
    start_time = time.time()

    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent

    # Change to the root directory
    os.chdir(root_dir)

    # Run the tests with optimized settings
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--no-header",
        # Skip slow test collection warnings
        "-p",
        "no:warnings",
        # Disable coverage to speed up tests
        "--no-cov",
    ]

    # Add any command line arguments
    cmd.extend(sys.argv[1:])

    # Run the tests
    result = subprocess.run(cmd, check=False)

    # Print the time taken
    end_time = time.time()
    print(f"\nTests completed in {end_time - start_time:.2f} seconds")

    # Return the exit code
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
