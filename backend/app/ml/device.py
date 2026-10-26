"""
Hardware device selection and concurrency management.

Device discovery is independent of integrated graphics. CUDA is selected only when
the installed PyTorch runtime reports a usable NVIDIA CUDA device.
"""

import logging
import os
import platform
import shutil
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages execution device selection and resource boundaries."""

    def __init__(self, preferred_device: Optional[str] = None):
        profile = settings.PLANTGUARD_INFERENCE_PROFILE.lower()
        profile_device = {"cpu": "cpu", "cuda": "cuda:0", "remote": "cpu"}.get(profile)
        self.preferred_device = preferred_device or profile_device or settings.PLANTGUARD_DEVICE
        self._active_device = self._resolve_device()
        self._apply_resource_limits()

    def _resolve_device(self) -> str:
        """Resolve the safest target compute device."""
        preferred = self.preferred_device.lower()
        if preferred == "cpu":
            logger.info("Using explicitly configured device: %s", self.preferred_device)
            return "cpu"
        if preferred in ("cuda", "cuda:0"):
            # Preserve explicit intent. Capability checks report an unusable CUDA
            # runtime instead of silently turning this into CPU inference.
            return "cuda:0"
        if preferred in ("directml", "openvino"):
            raise ValueError(f"Runtime '{preferred}' has no configured PlantGuard model adapter")
        if preferred != "auto":
            raise ValueError(f"Unsupported PlantGuard device profile '{preferred}'")

        # Check CUDA availability without crashing if torch is absent
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info("CUDA GPU detected: %s", device_name)
                return "cuda:0"
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("CUDA probe encountered error, falling back to CPU: %s", exc)

        logger.info("Using CPU execution mode; integrated graphics are not treated as CUDA")
        return "cpu"

    def _apply_resource_limits(self) -> None:
        """Configure thread bounding for CPU execution on Vivobook laptop."""
        if "cpu" in self._active_device:
            # Reserve at least 2 cores for OS/FastAPI responsiveness
            cpu_count = os.cpu_count() or 4
            allocated_threads = max(1, min(4, cpu_count - 2))
            
            try:
                import torch
                torch.set_num_threads(allocated_threads)
                logger.info("Bound PyTorch CPU threads to: %d", allocated_threads)
            except ImportError:
                pass

    @property
    def active_device(self) -> str:
        """Return the active compute device string."""
        return self._active_device

    def is_cuda(self) -> bool:
        """True if running on a CUDA GPU."""
        return "cuda" in self._active_device

    def get_hardware_summary(self) -> Dict[str, Any]:
        """Return host hardware and memory diagnostics."""
        total_disk, _, free_disk = shutil.disk_usage(".")
        summary = {
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "active_device": self._active_device,
            "cuda_available": False,
            "disk_free_gb": round(free_disk / (1024 ** 3), 2),
            "disk_total_gb": round(total_disk / (1024 ** 3), 2),
            "ram_total_gb": None,
            "ram_available_gb": None,
        }

        try:
            import psutil
            vm = psutil.virtual_memory()
            summary["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
            summary["ram_available_gb"] = round(vm.available / (1024 ** 3), 2)
        except (ImportError, OSError):
            pass

        try:
            import torch
            summary["cuda_available"] = torch.cuda.is_available()
            if torch.cuda.is_available():
                summary["cuda_device_name"] = torch.cuda.get_device_name(0)
        except (ImportError, OSError, RuntimeError):
            pass

        return summary


# Default singleton instance
device_manager = DeviceManager()
