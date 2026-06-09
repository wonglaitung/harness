#!/usr/bin/env python
"""
Download tiktoken encoding files for bundling with PyInstaller.

This script downloads the encoding files that tiktoken needs at runtime.
The files are saved to resources/tiktoken_cache/ for bundling.
"""

import hashlib
import os
import urllib.request
from pathlib import Path


# Encoding files needed by tiktoken
ENCODINGS = {
    "cl100k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken",
        "hash": "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7",
    },
    "o200k_base": {
        "url": "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken",
        "hash": "a45e2446f0a60e51d2d46bce78a0a17af0a37b2013a7c6f504c14c61a53c8c65",
    },
}


def download_file(url: str, expected_hash: str, output_path: Path) -> bool:
    """Download a file and verify its hash."""
    print(f"Downloading {url}...")

    try:
        urllib.request.urlretrieve(url, output_path)
    except Exception as e:
        print(f"  Error downloading: {e}")
        return False

    # Verify hash
    with open(output_path, "rb") as f:
        content = f.read()
        actual_hash = hashlib.sha256(content).hexdigest()

    if actual_hash != expected_hash:
        print(f"  Hash mismatch! Expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
        output_path.unlink()
        return False

    print(f"  Downloaded and verified: {output_path.name}")
    return True


def main():
    script_dir = Path(__file__).parent
    cache_dir = script_dir / "resources" / "tiktoken_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading tiktoken encoding files to {cache_dir}...\n")

    success = True
    for name, info in ENCODINGS.items():
        # tiktoken uses SHA1 of URL as filename
        url_hash = hashlib.sha1(info["url"].encode()).hexdigest()
        output_path = cache_dir / url_hash

        if output_path.exists():
            print(f"  {name}: already exists, skipping")
            continue

        if not download_file(info["url"], info["hash"], output_path):
            success = False

    print()
    if success:
        print("All encoding files downloaded successfully!")
    else:
        print("Some downloads failed. Check your internet connection.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
