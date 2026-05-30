#!/usr/bin/env python
"""
Build script for Harness Client.

Usage:
    python build.py          # Build the client
    python build.py --clean  # Clean build artifacts
"""

import subprocess
import sys
import shutil
from pathlib import Path


def clean():
    """Clean build artifacts."""
    dirs_to_remove = ["build", "dist", "__pycache__"]
    for d in dirs_to_remove:
        path = Path(d)
        if path.exists():
            shutil.rmtree(path)
            print(f"Removed: {path}")

    # Remove .spec backup files
    for spec_backup in Path(".").glob("*.spec.bak"):
        spec_backup.unlink()
        print(f"Removed: {spec_backup}")

    print("✅ Clean complete")


def build():
    """Build the client executable."""
    print("Building Harness Client...")

    # Run PyInstaller
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "harness-client.spec", "--noconfirm"],
        cwd=Path(__file__).parent,
    )

    if result.returncode == 0:
        print("\n✅ Build successful!")
        print("Output: dist/HarnessClient.exe")
    else:
        print("\n❌ Build failed!")
        sys.exit(1)


def main():
    if "--clean" in sys.argv:
        clean()
    else:
        build()


if __name__ == "__main__":
    main()
