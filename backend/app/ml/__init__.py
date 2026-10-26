"""ML Foundation package for PlantGuard AI."""

from .device import DeviceManager, device_manager
from .ood import OODDetector
from .pipeline import PlantAnalysisPipeline
from .registry import ModelRegistry, model_registry
from .severity import SeverityEstimator

__all__ = [
    "DeviceManager",
    "device_manager",
    "ModelRegistry",
    "model_registry",
    "OODDetector",
    "PlantAnalysisPipeline",
    "SeverityEstimator",
]
