"""Hash registered original/variant files in bounded chunks without loading tensors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path, chunk_bytes: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_bytes):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/model_manifest.json"))
    parser.add_argument("--max-total-bytes", type=int, required=True,
                        help="Explicit upper bound for checkpoint bytes read")
    parser.add_argument("--allow-reparse-points", action="store_true",
                        help="Explicitly permit cloud/reparse-point file reads")
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else root / args.manifest
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    registered: dict[str, Path] = {}
    total_bytes = 0
    for model_id, model in data["models"].items():
        original = model["original_checkpoint"]
        paths = {original["path"]}
        paths.update(variant["path"] for variant in model["variants"])
        for relative in paths:
            path = (root / relative).resolve(strict=True)
            if not path.is_relative_to(root):
                raise SystemExit(f"Refusing artifact outside repository root: {relative}")
            attributes = getattr(path.stat(), "st_file_attributes", 0)
            is_reparse = bool(attributes & getattr(stat_module(), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
            if is_reparse and not args.allow_reparse_points:
                raise SystemExit(f"Cloud/reparse-point read requires --allow-reparse-points: {relative}")
            total_bytes += path.stat().st_size
            registered[f"{model_id}:{relative}"] = path
    if total_bytes > args.max_total_bytes:
        raise SystemExit(f"Registered files total {total_bytes} bytes, above --max-total-bytes")

    hashes = {key: sha256_file(path) for key, path in registered.items()}
    for model_id, model in data["models"].items():
        original = model["original_checkpoint"]
        original_hash = hashes[f"{model_id}:{original['path']}"]
        original["sha256"] = original_hash
        original["sha256_status"] = "verified_by_streaming_sha256"
        for variant in model["variants"]:
            variant["sha256"] = hashes[f"{model_id}:{variant['path']}"]
            variant["sha256_status"] = "verified_by_streaming_sha256"
            variant["rollback_target"] = original["path"] if variant["path"] != original["path"] else None
    data["manifest_status"] = "checksums_recorded"
    data["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    try:
        data["source_revision"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        data["source_revision"] = None

    fd, temporary_name = tempfile.mkstemp(prefix="model-manifest-", suffix=".tmp", dir=manifest_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary_name).replace(manifest_path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)

    print(json.dumps({"manifest": manifest_path.relative_to(root).as_posix(),
                      "bytes_hashed": total_bytes, "artifact_count": len(registered),
                      "status": data["manifest_status"]}, indent=2))
    return 0


def stat_module():
    # Keep the script importable on Windows and non-Windows hosts.
    import stat
    return stat


if __name__ == "__main__":
    raise SystemExit(main())
