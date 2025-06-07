#!/usr/bin/env python3
"""
Build Tailwind CSS using standalone binary (no npm required).
"""

import subprocess
import sys
from pathlib import Path


def build_tailwind():
    """Build Tailwind CSS with standalone binary."""
    niamoto_root = Path(__file__).parent.parent
    binary_path = niamoto_root / "tailwindcss-macos-arm64"

    if not binary_path.exists():
        print("❌ Tailwind binary not found!")
        print("Please download it first with:")
        print(
            "curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.13/tailwindcss-macos-arm64"
        )
        print("chmod +x tailwindcss-macos-arm64")
        return False

    cmd = [
        str(binary_path),
        "-i",
        "./src/niamoto/publish/assets/css/vendor/tailwind/input.css",
        "-o",
        "./src/niamoto/publish/assets/css/vendor/tailwind/tailwind.min.css",
        "-c",
        "./tailwind.config.js",
        "--minify",
    ]

    print("🎨 Building Tailwind CSS (standalone)...")

    try:
        result = subprocess.run(cmd, cwd=niamoto_root, capture_output=True, text=True)

        if result.returncode == 0:
            output_file = (
                niamoto_root
                / "src/niamoto/publish/assets/css/vendor/tailwind/tailwind.min.css"
            )
            size_kb = output_file.stat().st_size // 1024
            print(f"✅ Success! ({size_kb} KB)")
            return True
        else:
            print(f"❌ Build failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = build_tailwind()
    sys.exit(0 if success else 1)
