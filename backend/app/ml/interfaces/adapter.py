"""
Common Model Interface & Adapter Contract.

Defines the explicit protocol and lifecycle specification that every model adapter
(Leaf Filter, Disease Classifier, Disease Segmenter, SAM) must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class ModelLoadingStatus(str, Enum):
    """Lifecycle state of an adapter's underlying neural network weights."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"
    DISABLED = "disabled"


class FailureBehavior(str, Enum):
    """Only fail-fast behavior is supported for model-backed inference."""
    FAIL_FAST = "fail_fast"


class EvaluationStatus(str, Enum):
    """Operational validation status of the artifact."""
    VERIFIED = "verified"         # Formally benchmarked on test data
    EXPERIMENTAL = "experimental" # Checkpoint exists but not fully benchmarked
    UNTESTED = "untested"         # Raw checkpoint loaded without verification


@dataclass(frozen=True)
class PreprocessingSpec:
    """Standardized preprocessing specification for vision models."""
    target_size: Tuple[int, int]  # (height, width)
    mean: Tuple[float, float, float] = (0.485, 0.456, 0.406)  # ImageNet standard
    std: Tuple[float, float, float] = (0.229, 0.224, 0.225)
    color_mode: str = "RGB"
    normalization_range: Tuple[float, float] = (0.0, 1.0)
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContractSpec:
    """Input or output tensor/data format description."""
    data_type: str                # e.g., "np.ndarray[uint8]", "torch.Tensor[float32]"
    shape: Tuple[Union[int, str], ...] # e.g., (1, 3, 224, 224) or (1, 38)
    description: str


class BaseModelAdapter(ABC):
    """
    Abstract Model Adapter Contract.

    Every neural model plugged into PlantGuard AI conforms to this uniform interface.
    """

    def __init__(
        self,
        name: str,
        artifact_path: Path,
        artifact_version: str,
        device_requirements: str = "cpu",
        failure_behavior: FailureBehavior = FailureBehavior.FAIL_FAST,
        evaluation_status: EvaluationStatus = EvaluationStatus.EXPERIMENTAL,
    ):
        self.name = name
        self.artifact_path = Path(artifact_path)
        self.artifact_version = artifact_version
        self.device_requirements = device_requirements
        self.failure_behavior = failure_behavior
        self.evaluation_status = evaluation_status
        self.loading_status = ModelLoadingStatus.UNLOADED
        self.active_device: Optional[str] = None
        self.last_error: Optional[str] = None
        # Adapters may report a machine-readable load failure. The service does
        # not guess error categories by searching human-readable error strings.
        self.load_error_code = None

    @abstractmethod
    def get_input_contract(self) -> ContractSpec:
        """Specify expected input type and dimension constraints."""
        pass

    @abstractmethod
    def get_preprocessing_spec(self) -> PreprocessingSpec:
        """Specify normalization, resizing, and color space conversion requirements."""
        pass

    @abstractmethod
    def get_output_contract(self) -> ContractSpec:
        """Specify produced output type and dimension constraints."""
        pass

    @abstractmethod
    def get_class_mapping(self) -> Optional[Dict[int, str]]:
        """Return integer index to string class name dictionary, if categorical."""
        pass

    @abstractmethod
    def load(self, target_device: str = "cpu") -> bool:
        """
        Load model weights into host memory / target device.
        Must return an explicit failure when the requested runtime is unsupported.
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """
        Evict model weights from RAM / VRAM to preserve memory on constrained devices.
        """
        pass

    @abstractmethod
    def predict(self, preprocessed_input: Any) -> Any:
        """
        Execute forward inference pass on preprocessed inputs.
        """
        pass

    def preprocess(self, raw_rgb_image: np.ndarray) -> Any:
        """
        Standardized preprocessing method using the PreprocessingSpec.
        Can be overridden for custom adapter pipelines.
        """
        if (not isinstance(raw_rgb_image, np.ndarray) or raw_rgb_image.ndim != 3
                or raw_rgb_image.shape[2] != 3 or raw_rgb_image.dtype != np.uint8
                or raw_rgb_image.shape[0] == 0 or raw_rgb_image.shape[1] == 0):
            raise ValueError("preprocess expects a non-empty RGB uint8 image (H, W, 3)")
        spec = self.get_preprocessing_spec()
        # Default numpy resizing and normalization
        from PIL import Image
        pil_img = Image.fromarray(raw_rgb_image).convert(spec.color_mode)
        resized = pil_img.resize((spec.target_size[1], spec.target_size[0]), Image.Resampling.BILINEAR)
        arr = np.array(resized, dtype=np.float32) / 255.0
        
        # Normalize
        mean = np.array(spec.mean, dtype=np.float32)
        std = np.array(spec.std, dtype=np.float32)
        normalized = (arr - mean) / std
        
        # Return channel-first (C, H, W)
        chw = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(chw, axis=0)

    def is_ready(self) -> bool:
        """Check if weights are successfully loaded and ready for prediction."""
        return self.loading_status == ModelLoadingStatus.READY

    def get_metadata(self) -> Dict[str, Any]:
        """Inspection dictionary for health reporting and model registry status."""
        return {
            "name": self.name,
            "artifact_path": str(self.artifact_path),
            "artifact_exists": self.artifact_path.exists(),
            "artifact_size_bytes": self.artifact_path.stat().st_size if self.artifact_path.exists() else 0,
            "artifact_version": self.artifact_version,
            "device_requirements": self.device_requirements,
            "active_device": self.active_device,
            "loading_status": self.loading_status.value,
            "failure_behavior": self.failure_behavior.value,
            "evaluation_status": self.evaluation_status.value,
            "last_error": self.last_error,
        }
