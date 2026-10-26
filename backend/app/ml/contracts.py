"""Framework-neutral contracts for the inference service boundary."""

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np


@dataclass(frozen=True)
class LeafCandidate:
    mask: np.ndarray
    bbox: tuple[float, float, float, float]  # normalized ymin, xmin, ymax, xmax
    sam_score: float
    area_pixels: int
    model_variant: str


class InferenceService(Protocol):
    """Application-facing interface; callers do not select a device or model library."""

    def analyze(self, image: np.ndarray, *, analysis_id: str | None = None): ...


class CandidateGenerator(Protocol):
    def generate(self, image: np.ndarray) -> Sequence[LeafCandidate]: ...
