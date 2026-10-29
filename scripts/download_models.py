#!/usr/bin/env python3
"""
scripts/download_models.py

Download missing model files and verify their SHA‑256 checksums.

The script reads `artifacts/manifest.json`, which must contain entries like:
{
    "model_name": {
        "url": "https://example.com/path/to/model.pt",
        "sha256": "ab12...78",
        "path": "artifacts/model_name.pt"  # optional, defaults to artifacts/<name>
    },
    ...
}
"""

import hashlib
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path: Path, expected: str) -> bool:
    return sha256_of_file(path).lower() == expected.lower()


def download(url: str, dest: Path):
    req = Request(url, headers={"User-Agent": "PlantGuardModelDownloader/1.0"})
    with urlopen(req) as resp, dest.open("wb") as out:
        out.write(resp.read())


def main():
    repo_root = Path(__file__).resolve().parent.parent
    manifest_path = repo_root / "artifacts" / "manifest.json"

    if not manifest_path.is_file():
        print(f"❌ manifest not found at {manifest_path}", file=sys.stderr)
        sys.exit(1)

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    # Handle legacy format where the manifest was a list containing a single dict.
    if isinstance(manifest, list) and manifest:
        manifest = manifest[0]

    # The manifest wraps model entries under a "models" key.
    models = manifest.get("models", {})
    if not isinstance(models, dict):
        print("❌ unexpected manifest format: 'models' is not a dict", file=sys.stderr)
        sys.exit(1)

    for name, entry in models.items():
        url = entry.get("url")
        expected_hash = entry.get("sha256")
        if not url or not expected_hash:
            print(f"⚠️  Skipping {name}: missing url or sha256", file=sys.stderr)
            continue

        target_rel = entry.get("path", f"artifacts/{name}")
        target_path = repo_root / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if target_path.is_file() and verify_checksum(target_path, expected_hash):
            print(f"✅ {name} already present and verified")
            continue

        print(f"⬇️  Downloading {name} from {url} …")
        try:
            download(url, target_path)
        except Exception as exc:
            print(f"❌ failed to download {name}: {exc}", file=sys.stderr)
            continue

        if verify_checksum(target_path, expected_hash):
            print(f"✅ {name} downloaded and checksum verified")
        else:
            print(f"❌ checksum mismatch for {name}", file=sys.stderr)
            target_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

