"""Framework-neutral contracts for the inference service boundary."""

from dataclasses import dataclass
import math
from typing import Generic, Mapping, Protocol, Sequence, TypeVar

import numpy as np

ResultT = TypeVar("ResultT")


@dataclass(frozen=True)
class LeafCandidate:
    mask: np.ndarray
    bbox: tuple[float, float, float, float]  # normalized ymin, xmin, ymax, xmax
    sam_score: float
    area_pixels: int
    model_variant: str

    def __post_init__(self) -> None:
        if not isinstance(self.mask, np.ndarray) or self.mask.ndim != 2 or not self.mask.size:
            raise ValueError("LeafCandidate.mask must be a non-empty 2D array")
        if len(self.bbox) != 4 or not all(math.isfinite(v) for v in self.bbox):
            raise ValueError("LeafCandidate.bbox must contain four finite normalized coordinates")
        y0, x0, y1, x1 = self.bbox
        if not (0 <= y0 < y1 <= 1 and 0 <= x0 < x1 <= 1):
            raise ValueError("LeafCandidate.bbox coordinates are out of order or range")
        if not math.isfinite(self.sam_score) or not 0 <= self.sam_score <= 1:
            raise ValueError("LeafCandidate.sam_score must be in [0, 1]")
        if self.area_pixels <= 0 or not self.model_variant:
            raise ValueError("LeafCandidate requires a positive area and model version")


@dataclass(frozen=True)
class LeafFilterScore:
    """Validated positive-class score for one SAM candidate."""

    confidence: float
    accepted: bool
    model_version: str

    def __post_init__(self) -> None:
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1 or not self.model_version:
            raise ValueError("Leaf filter score must be finite, normalized, and versioned")


@dataclass(frozen=True)
class DiseasePrediction:
    """Validated classifier result with its exact ordered class mapping."""

    class_index: int
    class_name: str
    confidence: float
    probabilities: tuple[float, ...]
    model_version: str

    def __post_init__(self) -> None:
        if not 0 <= self.class_index < 38 or not self.class_name or not self.model_version:
            raise ValueError("Disease prediction has an invalid class identity")
        if len(self.probabilities) != 38 or not all(math.isfinite(p) and 0 <= p <= 1 for p in self.probabilities):
            raise ValueError("Disease prediction must contain 38 finite probabilities")
        if not math.isclose(sum(self.probabilities), 1.0, abs_tol=1e-3):
            raise ValueError("Disease prediction probabilities must sum to one")
        if not math.isclose(self.confidence, self.probabilities[self.class_index], abs_tol=1e-6):
            raise ValueError("Disease prediction confidence must match its selected class")


@dataclass(frozen=True)
class SegmentationPrediction:
    """Decoded semantic class mask; IDs retain the checkpoint's label mapping."""

    class_mask: np.ndarray
    label_mapping: Mapping[int, str]
    model_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.class_mask, np.ndarray) or self.class_mask.ndim != 2 or not self.class_mask.size:
            raise ValueError("Segmentation class mask must be a non-empty 2D array")
        if not self.label_mapping or not self.model_version:
            raise ValueError("Segmentation prediction requires a label mapping and model version")
        if not np.issubdtype(self.class_mask.dtype, np.integer) and self.class_mask.dtype != np.bool_:
            raise ValueError("Segmentation class mask must contain integer IDs")
        if not np.isin(self.class_mask, list(self.label_mapping)).all():
            raise ValueError("Segmentation class mask contains an unmapped label ID")


@dataclass(frozen=True)
class StageMetadata:
    """Execution facts attached to validated stage outputs."""

    stage: str
    model_version: str
    runtime: str
    duration_ms: int

    def __post_init__(self) -> None:
        if not self.stage or not self.model_version or not self.runtime or self.duration_ms < 0:
            raise ValueError("Stage metadata must identify stage/model/runtime and non-negative duration")


@dataclass(frozen=True)
class StageOutput(Generic[ResultT]):
    """Typed value plus runtime/version/timing metadata for one completed stage."""

    value: ResultT
    metadata: StageMetadata
    warnings: tuple[str, ...] = ()


class InferenceService(Protocol):
    """Application-facing interface; callers do not select a device or model library."""

    def analyze(self, image: np.ndarray, *, analysis_id: str | None = None): ...


class CandidateGenerator(Protocol):
    def generate(self, image: np.ndarray) -> Sequence[LeafCandidate]: ...


class SamModel(Protocol):
    """Raw SAM adapter boundary. Service validates and converts proposals."""

    name: str
    artifact_version: str

    def predict(self, raw_rgb_image: np.ndarray) -> Sequence[Mapping[str, object]]: ...


class ProbabilityModel(Protocol):
    """DINO adapters return a batch of class probabilities after preprocessing."""

    name: str
    artifact_version: str

    def predict(self, preprocessed_input: np.ndarray) -> np.ndarray: ...


class SegmentationModel(Protocol):
    """SegFormer returns decoded integer class IDs aligned to requested dimensions."""

    name: str
    artifact_version: str

    def predict(self, preprocessed_input: np.ndarray, *, original_shape: tuple[int, int]) -> np.ndarray: ...
