"""Lightweight artifact/runtime readiness report; this script does not load models."""

import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ml.device import device_manager
from app.ml.registry import model_registry


def main() -> int:
    report = model_registry.get_readiness_report()
    report["hardware"] = device_manager.get_hardware_summary()
    print(json.dumps(report, indent=2, default=str))
    print("This is an artifact/runtime metadata report, not a model inference test.")
    print("Use scripts/sam2_gpu_smoke.py on the RTX host for actual SAM 2.1 inference.")
    return 0 if report["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
