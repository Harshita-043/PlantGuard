"""
Model Registry & Readiness Reporting for PlantGuard AI.

Responsible for:
1. Artifact inventory validation & discovery.
2. Lazy, sequential adapter instantiation with bounded memory usage.
3. Health & readiness reporting for all pipeline components.
"""

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.ml.device import device_manager
from app.ml.interfaces.adapter import (
    BaseModelAdapter,
    EvaluationStatus,
    FailureBehavior,
    ModelLoadingStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArtifactDescriptor:
    """Discovered on-disk artifact record."""
    name: str
    relative_path: str
    resolved_path: Optional[Path]
    size_bytes: int
    is_valid: bool
    format_type: str
    metadata: Dict[str, Any]


class ModelRegistry:
    """
    Central registry for machine learning models and pipelines.
    Enforces sequential, memory-conscious execution for the Vivobook environment.
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or self._locate_workspace_root()
        self._adapters: Dict[str, BaseModelAdapter] = {}
        self._artifacts_cache: Optional[Dict[str, ArtifactDescriptor]] = None
        logger.info("Initialized ModelRegistry at root: %s", self.workspace_root)

    def _locate_workspace_root(self) -> Path:
        """Dynamically detect workspace root from current working directory or file anchor."""
        current = Path.cwd().resolve()
        for candidate in [current, current.parent, Path(__file__).resolve().parents[3]]:
            if (candidate / "artifacts").exists() or (candidate / "outputs").exists():
                return candidate
        return current

    def get_artifact_inventory(self, force_refresh: bool = False) -> Dict[str, ArtifactDescriptor]:
        """
        Scan and validate all physical model artifacts without loading tensors into RAM.
        """
        if self._artifacts_cache is not None and not force_refresh:
            return self._artifacts_cache

        inventory = {}

        # 1. DINOv2 Leaf Filter
        lf_path = self.workspace_root / "artifacts" / "dino_leaf_filter" / "dino_leaf_filter.pt"
        lf_v2_path = self.workspace_root / "artifacts" / "dino_leaf_filter" / "dino_leaf_filter_v2.pt"
        chosen_lf = lf_v2_path if lf_v2_path.exists() else lf_path
        inventory["leaf_filter"] = ArtifactDescriptor(
            name="DINOv2 Small Leaf Filter",
            relative_path=str(chosen_lf.relative_to(self.workspace_root) if chosen_lf.exists() else chosen_lf),
            resolved_path=chosen_lf if chosen_lf.exists() else None,
            size_bytes=chosen_lf.stat().st_size if chosen_lf.exists() else 0,
            is_valid=chosen_lf.exists() and chosen_lf.stat().st_size > 10_000_000,
            format_type="pytorch_zip",
            metadata={"classes": ["negative", "positive"], "backbone": "dinov2_vits14"},
        )

        # 2. DINOv2 Disease Classifier
        dc_path = self.workspace_root / "artifacts" / "dino_disease" / "dino_disease_classifier.pt"
        classes_path = self.workspace_root / "artifacts" / "dino_disease" / "classes.json"
        classes = []
        if classes_path.exists():
            try:
                with open(classes_path, "r", encoding="utf-8") as f:
                    classes = json.load(f)
            except Exception:
                pass

        inventory["disease_classifier"] = ArtifactDescriptor(
            name="DINOv2 Base Disease Classifier",
            relative_path=str(dc_path.relative_to(self.workspace_root) if dc_path.exists() else dc_path),
            resolved_path=dc_path if dc_path.exists() else None,
            size_bytes=dc_path.stat().st_size if dc_path.exists() else 0,
            is_valid=dc_path.exists() and dc_path.stat().st_size > 50_000_000 and len(classes) == 38,
            format_type="pytorch_zip",
            metadata={"num_classes": len(classes), "classes": classes, "backbone": "dinov2_vitb14"},
        )

        # 3. SegFormer-B0 Disease Segmentation
        sf_path = self.workspace_root / "outputs" / "segformer_plantseg" / "best_model" / "model.safetensors"
        sf_config_path = self.workspace_root / "outputs" / "segformer_plantseg" / "best_model" / "config.json"
        sf_pre_path = self.workspace_root / "outputs" / "segformer_plantseg" / "best_model" / "preprocessing.json"
        sf_config = {}
        if sf_config_path.exists():
            try:
                with open(sf_config_path, "r", encoding="utf-8") as f:
                    sf_config = json.load(f)
            except Exception:
                pass

        inventory["disease_segmentation"] = ArtifactDescriptor(
            name="SegFormer-B0 PlantSeg Disease Segmenter",
            relative_path=str(sf_path.relative_to(self.workspace_root) if sf_path.exists() else sf_path),
            resolved_path=sf_path if sf_path.exists() else None,
            size_bytes=sf_path.stat().st_size if sf_path.exists() else 0,
            is_valid=sf_path.exists() and sf_path.stat().st_size > 1_000_000 and sf_config_path.exists(),
            format_type="safetensors",
            metadata={
                "model_type": sf_config.get("model_type", "segformer"),
                "num_classes": 2,
                "id2label": sf_config.get("id2label", {"0": "background", "1": "diseased_region"}),
            },
        )

        # 4. SAM 2.1 Hiera Base+
        sam_path = self.workspace_root / "artifacts" / "sam2" / "sam2.1_hiera_base_plus.pt"
        inventory["leaf_instance_segmentation"] = ArtifactDescriptor(
            name="SAM 2.1 Hiera Base+",
            relative_path=str(sam_path.relative_to(self.workspace_root) if sam_path.exists() else sam_path),
            resolved_path=sam_path if sam_path.exists() else None,
            size_bytes=sam_path.stat().st_size if sam_path.exists() else 0,
            is_valid=sam_path.exists() and sam_path.stat().st_size > 100_000_000,
            format_type="pytorch_zip",
            metadata={"backbone": "sam2.1_hiera_base_plus", "device_recommendation": "cuda_only_for_full_grid"},
        )

        self._artifacts_cache = inventory
        return inventory

    def register_adapter(self, key: str, adapter: BaseModelAdapter) -> None:
        """Register a model adapter instance."""
        self._adapters[key] = adapter
        logger.info("Registered adapter '%s' (%s)", key, adapter.name)

    def get_adapter(self, key: str) -> Optional[BaseModelAdapter]:
        """Retrieve a registered adapter by key."""
        return self._adapters.get(key)

    def get_readiness_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive health and readiness report for backend diagnostics.
        """
        inventory = self.get_artifact_inventory()
        hardware = device_manager.get_hardware_summary()

        torch_available = False
        torch_version = None
        try:
            import torch
            torch_available = True
            torch_version = torch.__version__
        except ImportError:
            pass

        components = {}
        for key, desc in inventory.items():
            adapter = self._adapters.get(key)
            loading_status = getattr(adapter, "loading_status", ModelLoadingStatus.UNLOADED) if adapter else ModelLoadingStatus.UNLOADED
            evaluation_status = getattr(adapter, "evaluation_status", EvaluationStatus.UNTESTED) if adapter else EvaluationStatus.UNTESTED
            components[key] = {
                "name": desc.name,
                "artifact_path": desc.relative_path,
                "artifact_exists": desc.resolved_path is not None,
                "artifact_valid": desc.is_valid,
                "size_mb": round(desc.size_bytes / (1024 * 1024), 2),
                "format": desc.format_type,
                "loading_status": getattr(loading_status, "value", str(loading_status)),
                "evaluation_status": getattr(evaluation_status, "value", str(evaluation_status)),
            }

        all_artifacts_present = all(c["artifact_exists"] for c in components.values())
        all_artifacts_valid = all(c["artifact_valid"] for c in components.values())
        all_models_loaded = bool(components) and all(
            c["loading_status"] == ModelLoadingStatus.READY.value for c in components.values()
        )

        return {
            # Artifact presence is not model readiness; adapters load lazily per inference.
            "status": "ready" if all_artifacts_valid and torch_available and all_models_loaded else "degraded",
            "runtime_environment": {
                "python_runtime_torch_ready": torch_available,
                "torch_version": torch_version,
                "active_device": hardware["active_device"],
                "cuda_available": hardware["cuda_available"],
                "vivobook_cpu_mode": not hardware["cuda_available"],
            },
            "hardware": hardware,
            "components": components,
            "efficientnet_rule_enforced": True,
        }


# Singleton registry instance
model_registry = ModelRegistry()
