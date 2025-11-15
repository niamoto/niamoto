#!/usr/bin/env python3
"""
Development script to run the Niamoto GUI API with proper instance context.

This script allows running the FastAPI backend in development mode while
maintaining the correct instance context, even when not launched from within
the instance directory.

Usage:
    # Using command-line argument
    python scripts/dev_api.py --instance test-instance/niamoto-nc

    # Using environment variable
    export NIAMOTO_HOME=/path/to/instance
    python scripts/dev_api.py

    # From the instance directory (auto-detect)
    cd test-instance/niamoto-nc
    python ../../scripts/dev_api.py
"""

import os
import sys
import argparse
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))


def main():
    parser = argparse.ArgumentParser(
        description="Run Niamoto GUI API in development mode"
    )
    parser.add_argument(
        "--instance",
        type=str,
        help="Path to the Niamoto instance directory (absolute or relative to repo root)",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Port to run the API on (default: 8080)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload on code changes",
    )

    args = parser.parse_args()

    # Determine instance path
    instance_path = None

    # Priority 1: Command-line argument
    if args.instance:
        instance_path = Path(args.instance)
        if not instance_path.is_absolute():
            instance_path = repo_root / instance_path
    # Priority 2: NIAMOTO_HOME environment variable
    elif os.environ.get("NIAMOTO_HOME"):
        instance_path = Path(os.environ["NIAMOTO_HOME"])
    # Priority 3: Current working directory
    else:
        instance_path = Path.cwd()
        print(f"⚠️  No instance specified, using current directory: {instance_path}")

    # Validate instance path
    instance_path = instance_path.resolve()
    if not instance_path.exists():
        print(f"❌ Error: Instance directory does not exist: {instance_path}")
        sys.exit(1)

    # Check for config directory (optional, but helpful warning)
    config_dir = instance_path / "config"
    if not config_dir.exists():
        print(f"⚠️  Warning: No config directory found at {config_dir}")
        print("   This might not be a valid Niamoto instance, but continuing anyway...")

    # Set the working directory context before importing the app
    from niamoto.gui.api.context import set_working_directory

    set_working_directory(instance_path)
    print(f"✅ Instance context set to: {instance_path}")

    # Also set NIAMOTO_HOME for any subprocess or code that reads it directly
    os.environ["NIAMOTO_HOME"] = str(instance_path)

    # Now import and run the app
    import uvicorn

    print("\n🚀 Starting Niamoto API in development mode...")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Reload: {not args.no_reload}")
    print(f"   Instance: {instance_path}")
    print(f"\n   API: http://{args.host}:{args.port}/api")
    print(f"   Docs: http://{args.host}:{args.port}/api/docs\n")

    uvicorn.run(
        "niamoto.gui.api.app:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        reload_dirs=[str(repo_root / "src")],
        log_level="info",
    )


if __name__ == "__main__":
    main()
