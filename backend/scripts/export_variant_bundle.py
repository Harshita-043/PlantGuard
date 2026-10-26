"""Export only checksum-verified, validated optimized variants into a clean bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--manifest", type=Path, default=Path("artifacts/model_manifest.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source_manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    output = args.output.resolve()
    if output.exists():
        parser.error("Output directory must be new and empty; existing paths are refused")
    data = json.loads(source_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=False)
    artifact_dir = output / "artifacts"
    artifact_dir.mkdir()
    checksums: list[tuple[str, str]] = []
    exported = []
    for model_id, model in data.get("models", {}).items():
        for variant in model.get("variants", []):
            if variant.get("kind") == "original":
                continue
            if variant.get("validation", {}).get("status") != "validated":
                raise SystemExit(f"Refusing unvalidated optimized variant: {model_id}/{variant.get('variant_id')}")
            expected = variant.get("sha256")
            if not isinstance(expected, str) or len(expected) != 64:
                raise SystemExit(f"Refusing optimized variant without SHA-256: {model_id}/{variant.get('variant_id')}")
            source = (root / variant["path"]).resolve(strict=True)
            if not source.is_relative_to(root) or not source.is_file() or _sha256(source).lower() != expected.lower():
                raise SystemExit(f"Optimized variant integrity verification failed: {model_id}/{variant.get('variant_id')}")
            relative = Path("artifacts") / "optimized_variants" / model_id / variant["variant_id"] / source.name
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if _sha256(destination).lower() != expected.lower():
                raise SystemExit(f"Copied variant checksum mismatch: {relative.as_posix()}")
            variant["path"] = relative.as_posix()
            exported.append(relative.as_posix())
            checksums.append((expected.lower(), relative.as_posix()))

    manifest_out = artifact_dir / "model_manifest.json"
    manifest_out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums.append((_sha256(manifest_out), "artifacts/model_manifest.json"))
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{digest}  {relative}\n" for digest, relative in sorted(checksums, key=lambda pair: pair[1])),
        encoding="utf-8",
    )
    (output / "BUNDLE_CONTENTS.txt").write_text(
        "Validated optimized variants only. Original model checkpoints are not included or modified.\n"
        + ("\n".join(exported) if exported else "No validated optimized variants were registered."),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output), "optimized_variants_exported": len(exported),
                      "checksums_file": str(output / "SHA256SUMS.txt")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
