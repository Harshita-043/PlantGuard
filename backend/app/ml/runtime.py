"""Read-only runtime capability reporting; never loads model checkpoints."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


_DISTRIBUTIONS = {
    "torch": "torch",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "safetensors": "safetensors",
    "sam2": "SAM-2",
    "mobile_sam": "mobile-sam",
    "timm": "timm",
    "onnxruntime": "onnxruntime",
    "openvino": "openvino",
    "directml": "torch-directml",
}


def _version(name: str) -> str | None:
    distribution = _DISTRIBUTIONS[name]
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _base_version(value: str | None) -> str | None:
    return value.split("+", 1)[0] if value else None


def _safetensors_supported(value: str | None) -> bool:
    if value is None:
        return False
    try:
        major, minor, *_ = (int(part) for part in value.split(".", 2))
        return (major, minor) >= (0, 5) and major < 1
    except ValueError:
        return False


def _onnxruntime_supported(value: str | None) -> bool:
    if value is None:
        return False
    try:
        major, minor, *_ = (int(part) for part in value.split(".", 2))
        return (major, minor) >= (1, 20) and major < 2
    except ValueError:
        return False


def _mps_available() -> bool:
    try:
        import torch
        return bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
    except (ImportError, OSError, RuntimeError):
        return False


@dataclass(frozen=True)
class RuntimeCapabilities:
    profile: str
    operating_system: str
    architecture: str
    cpu_model: str | None
    logical_cpu_count: int | None
    ram_total_gb: float | None
    ram_available_gb: float | None
    python_version: str
    supported_python_version: bool
    packages: dict[str, str | None]
    package_version_compatibility: dict[str, bool]
    inference_backends: dict[str, bool]
    cuda: dict[str, Any]
    mps: dict[str, bool]
    model_compatibility: dict[str, dict[str, Any]]
    configured_memory_limit_gb: float | None
    configured_concurrency: int
    remote: dict[str, Any]

    def public_dict(self) -> dict[str, Any]:
        """Return diagnostics-safe fields; no paths, tokens, or remote URL."""
        return asdict(self)


def collect_runtime_capabilities(
    *,
    profile: str = "auto",
    memory_limit_gb: float | None = None,
    concurrency: int = 1,
    remote_configured: bool = False,
    remote_status: str = "not_configured",
) -> RuntimeCapabilities:
    """Probe OS/runtime metadata without importing or loading PlantGuard models."""
    try:
        import psutil
        memory = psutil.virtual_memory()
        ram_total = round(memory.total / (1024 ** 3), 3)
        ram_available = round(memory.available / (1024 ** 3), 3)
    except (ImportError, OSError):
        ram_total = ram_available = None

    package_versions = {name: _version(name) for name in _DISTRIBUTIONS}
    installed = {name: _module_available(name) for name in _DISTRIBUTIONS}
    python_version = platform.python_version()
    python_supported = python_version.startswith("3.12.")
    version_checks = {
        "torch": _base_version(package_versions["torch"]) == "2.6.0",
        "torchvision": _base_version(package_versions["torchvision"]) == "0.21.0",
        "transformers": _base_version(package_versions["transformers"]) == "4.57.6",
        "safetensors": _safetensors_supported(package_versions["safetensors"]),
        "sam2": _base_version(package_versions["sam2"]) == "1.0",
        "mobile_sam": _base_version(package_versions["mobile_sam"]) == "1.0",
        "timm": _base_version(package_versions["timm"]) == "1.0.30",
        "onnxruntime": _onnxruntime_supported(package_versions["onnxruntime"]),
    }
    cuda: dict[str, Any] = {
        "available": None if not installed["torch"] else False,
        "pytorch_cuda_build": None,
        "device_name": None,
        "device_count": 0,
        "total_vram_gb": None,
        "available_vram_gb": None,
        "runtime_error": None,
    }
    if installed["torch"]:
        try:
            import torch
            cuda["pytorch_cuda_build"] = torch.version.cuda
            cuda["available"] = bool(torch.cuda.is_available())
            if cuda["available"]:
                cuda["device_count"] = torch.cuda.device_count()
                props = torch.cuda.get_device_properties(0)
                cuda["device_name"] = props.name
                cuda["total_vram_gb"] = round(props.total_memory / (1024 ** 3), 3)
                try:
                    free, total = torch.cuda.mem_get_info(0)
                    cuda["available_vram_gb"] = round(free / (1024 ** 3), 3)
                    cuda["total_vram_gb"] = round(total / (1024 ** 3), 3)
                except (AttributeError, RuntimeError):
                    pass
        except (ImportError, OSError, RuntimeError) as exc:
            cuda["runtime_error"] = type(exc).__name__

    sam_spec = None
    if installed["sam2"]:
        try:
            sam_spec = importlib.util.find_spec("sam2")
        except (ImportError, ValueError, ModuleNotFoundError):
            pass
    sam_config_present = False
    if sam_spec and sam_spec.origin:
        package_root = Path(sam_spec.origin).parent
        sam_config_present = (package_root / "configs" / "sam2.1" / "sam2.1_hiera_b+.yaml").is_file()

    cuda_available = cuda["available"] is True
    mps_available = _mps_available()
    mps = {"available": mps_available}
    model_compatibility = {
        "sam2_hiera_base_plus": {
            "cpu": {"status": "prerequisites_present" if python_supported and installed["torch"] and installed["sam2"] and sam_config_present and version_checks["torch"] and version_checks["sam2"] else "blocked",
                    "runtime_validation": "not_smoke_tested",
                    "requirements": ["Python 3.12", "torch==2.6.0", "sam2==1.0", "official_hiera_base_plus_config"]},
            "cuda": {"status": "prerequisites_present" if python_supported and installed["torch"] and installed["sam2"] and sam_config_present and cuda_available and version_checks["torch"] and version_checks["sam2"] else "blocked",
                     "runtime_validation": "not_smoke_tested",
                     "requirements": ["Python 3.12", "torch==2.6.0 CUDA build", "available_nvidia_cuda_device", "sam2==1.0", "official_hiera_base_plus_config"]},
            "config_present": sam_config_present,
        },
        "mobile_sam_vit_t": {
            "cpu": {
                "status": "prerequisites_present" if installed["torch"] and installed["mobile_sam"] and installed["timm"] and version_checks["mobile_sam"] and version_checks["timm"] else "blocked",
                "runtime_validation": "not_smoke_tested",
                "requirements": ["torch", "mobile_sam==1.0", "timm==1.0.30"],
            },
            "cuda": {
                "status": "prerequisites_present" if installed["torch"] and installed["mobile_sam"] and installed["timm"] and version_checks["mobile_sam"] and version_checks["timm"] and cuda_available else "blocked",
                "runtime_validation": "not_smoke_tested",
                "requirements": ["torch", "mobile_sam==1.0", "timm==1.0.30", "available_nvidia_cuda_device"],
            },
            "mps": {
                "status": "prerequisites_present" if installed["torch"] and installed["mobile_sam"] and installed["timm"] and version_checks["mobile_sam"] and version_checks["timm"] and mps_available else "blocked",
                "runtime_validation": "not_smoke_tested",
                "requirements": ["torch", "mobile_sam==1.0", "timm==1.0.30", "available_mps_device"],
            },
        },
        "dinov2_vits14_leaf_filter": {
            "cpu": {"status": "prerequisites_present" if python_supported and installed["torch"] and version_checks["torch"] else "blocked", "runtime_validation": "not_smoke_tested", "requirements": ["Python 3.12", "torch==2.6.0"]},
            "cuda": {"status": "prerequisites_present" if python_supported and installed["torch"] and cuda_available and version_checks["torch"] else "blocked", "runtime_validation": "not_smoke_tested", "requirements": ["Python 3.12", "torch==2.6.0 CUDA build", "available_nvidia_cuda_device"]},
        },
        "dinov2_vitb14_classifier": {
            "cpu": {"status": "prerequisites_present" if python_supported and installed["torch"] and version_checks["torch"] else "blocked", "runtime_validation": "not_smoke_tested", "requirements": ["Python 3.12", "torch==2.6.0"]},
            "cuda": {"status": "prerequisites_present" if python_supported and installed["torch"] and cuda_available and version_checks["torch"] else "blocked", "runtime_validation": "not_smoke_tested", "requirements": ["Python 3.12", "torch==2.6.0 CUDA build", "available_nvidia_cuda_device"]},
        },
        "segformer_b0_plantseg": {
            "cpu": {"status": "prerequisites_present" if python_supported and installed["torch"] and installed["transformers"] and installed["safetensors"] and version_checks["torch"] and version_checks["transformers"] and version_checks["safetensors"] else "blocked",
                    "runtime_validation": "not_smoke_tested",
                    "requirements": ["Python 3.12", "torch==2.6.0", "transformers==4.57.6", "safetensors>=0.5,<1"]},
            "cuda": {"status": "prerequisites_present" if python_supported and installed["torch"] and installed["transformers"] and installed["safetensors"] and cuda_available and version_checks["torch"] and version_checks["transformers"] and version_checks["safetensors"] else "blocked",
                     "runtime_validation": "not_smoke_tested",
                     "requirements": ["Python 3.12", "torch==2.6.0 CUDA build", "available_nvidia_cuda_device", "transformers==4.57.6", "safetensors>=0.5,<1"]},
        },
    }
    cpu_model = platform.processor() or None
    if not cpu_model and platform.system() == "Windows":
        cpu_model = os.environ.get("PROCESSOR_IDENTIFIER") or None

    return RuntimeCapabilities(
        profile=profile,
        operating_system=f"{platform.system()} {platform.release()}",
        architecture=platform.machine(),
        cpu_model=cpu_model,
        logical_cpu_count=os.cpu_count(),
        ram_total_gb=ram_total,
        ram_available_gb=ram_available,
        python_version=python_version,
        supported_python_version=python_supported,
        packages=package_versions,
        package_version_compatibility=version_checks,
        inference_backends={name: installed[name] for name in ("torch", "onnxruntime", "openvino", "directml")},
        cuda=cuda,
        mps=mps,
        model_compatibility=model_compatibility,
        configured_memory_limit_gb=memory_limit_gb,
        configured_concurrency=concurrency,
        remote={"configured": remote_configured, "status": remote_status},
    )
