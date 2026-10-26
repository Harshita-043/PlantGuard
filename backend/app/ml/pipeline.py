"""Compatibility facade for the lazy inference service."""

from pathlib import Path
from typing import Optional
from uuid import UUID

from app.ml.service import PlantAnalysisService
from app.storage.interface import ObjectStorage


class PlantAnalysisPipeline:
    """Retains the former pipeline entry point while using fail-closed inference."""

    def __init__(self, storage: Optional[ObjectStorage] = None, *, service: PlantAnalysisService | None = None):
        self.service = service or PlantAnalysisService(storage=storage)
        # Kept for callers that explicitly prepare/check a model before requesting inference.
        self.leaf_filter = self.service.leaf_filter
        self.classifier = self.service.classifier
        self.segmenter = self.service.segmenter
        self.sam_adapter = self.service.sam

    def execute_scan(self, image_bytes: bytes, analysis_id: UUID | None = None, user_id: UUID | None = None):
        # Mask storage is scoped using the analysis id; user ownership belongs to the API layer.
        return self.service.analyze_bytes(image_bytes, analysis_id=str(analysis_id) if analysis_id else None)
