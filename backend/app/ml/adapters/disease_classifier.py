"""
DINOv2 Base 38-Class Disease Classifier Model Adapter.

Performs fine-grained 38-class disease categorization on segmented leaf regions
using the DINOv2 Base backbone.
Artifact: `artifacts/dino_disease/dino_disease_classifier.pt` + `classes.json`.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from app.ml.errors import InferenceErrorCode

from app.ml.interfaces.adapter import (
    BaseModelAdapter,
    ContractSpec,
    EvaluationStatus,
    FailureBehavior,
    ModelLoadingStatus,
    PreprocessingSpec,
)

logger = logging.getLogger(__name__)


class DinoDiseaseClassifierAdapter(BaseModelAdapter):
    """
    Adapter for DINOv2 Base 38-class PlantVillage disease classifier.
    Backbone: dinov2_vitb14 (embed_dim=768, depth=12, num_heads=12).
    Classification Head: LayerNorm(768) -> Linear(768, 38) -> Softmax.
    Target resolution: 224x224 RGB.
    Output: Softmax probabilities across 38 classes.
    """

    def __init__(
        self,
        artifact_path: Optional[Path] = None,
        classes_path: Optional[Path] = None,
        artifact_version: str = "v1",
        failure_behavior: FailureBehavior = FailureBehavior.FAIL_FAST,
    ):
        path = artifact_path or self._resolve_default_path()
        super().__init__(
            name="dino_disease_classifier",
            artifact_path=path,
            artifact_version=artifact_version,
            device_requirements="cpu",
            failure_behavior=failure_behavior,
            evaluation_status=EvaluationStatus.UNTESTED,
        )
        self.classes_path = classes_path or self._resolve_classes_path()
        self._model = None
        self._class_names: List[str] = self._load_classes()

    def _resolve_default_path(self) -> Path:
        candidates = [
            Path("artifacts/dino_disease/dino_disease_classifier.pt"),
            Path("../artifacts/dino_disease/dino_disease_classifier.pt"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("artifacts/dino_disease/dino_disease_classifier.pt")

    def _resolve_classes_path(self) -> Path:
        candidates = [
            self.artifact_path.parent / "classes.json",
            Path("artifacts/dino_disease/classes.json"),
            Path("../artifacts/dino_disease/classes.json"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return self.artifact_path.parent / "classes.json"

    def _load_classes(self) -> List[str]:
        if self.classes_path.exists():
            try:
                with open(self.classes_path, "r", encoding="utf-8") as f:
                    classes = json.load(f)
                if (isinstance(classes, list) and len(classes) == 38
                        and all(isinstance(label, str) and label for label in classes)
                        and len(set(classes)) == 38):
                    return classes
                logger.error("Classifier labels must be 38 unique non-empty strings")
            except Exception as e:
                logger.warning("Could not read classes.json: %s", e)
        return []

    def get_input_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="np.ndarray[float32]",
            shape=(1, 3, 224, 224),
            description="Normalized RGB tensor CHW format (ImageNet mean and std)",
        )

    def get_preprocessing_spec(self) -> PreprocessingSpec:
        return PreprocessingSpec(
            target_size=(224, 224),
            mean=(0.485, 0.456, 0.406),
            std=(0.229, 0.224, 0.225),
            color_mode="RGB",
            normalization_range=(0.0, 1.0),
        )

    def get_output_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="np.ndarray[float32]",
            shape=(1, max(1, len(self._class_names))),
            description="Softmax probability distribution across 38 PlantVillage disease classes",
        )

    def get_class_mapping(self) -> Optional[Dict[int, str]]:
        return {idx: name for idx, name in enumerate(self._class_names)}

    def load(self, target_device: str = "cpu") -> bool:
        """Load DINOv2 Disease Classifier weights into memory."""
        self.loading_status = ModelLoadingStatus.LOADING
        self.active_device = target_device
        self.last_error = None
        self.load_error_code = None

        if not self.artifact_path.exists():
            self.last_error = f"Artifact not found at {self.artifact_path}"
            self.load_error_code = InferenceErrorCode.MISSING_ARTIFACT
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False

        try:
            import torch
            from app.ml.architectures.dinov2 import build_dino_disease_classifier

            logger.info("Constructing DINOv2 Base model for %s...", self.artifact_path)
            model = build_dino_disease_classifier()
            if len(self._class_names) != 38:
                raise ValueError("Disease classifier requires the verified 38-class classes.json mapping")
            checkpoint = torch.load(str(self.artifact_path), map_location=target_device, weights_only=True)

            # Refresh classes from checkpoint if present
            if isinstance(checkpoint, dict) and "classes" in checkpoint and checkpoint["classes"] != self._class_names:
                raise ValueError("Checkpoint class order does not match classes.json")

            state_dict = checkpoint.get("state_dict", checkpoint)
            model.load_state_dict(state_dict, strict=True)
            model.to(target_device)
            model.eval()

            self._model = model
            self.loading_status = ModelLoadingStatus.READY
            logger.info("DINOv2 disease classifier loaded successfully on %s (strict=True, 38 classes)", target_device)
            return True
        except ImportError as e:
            self.last_error = f"PyTorch import failed: {e}"
            self.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False
        except Exception as exc:
            self.last_error = f"Failed to load DINOv2 disease classifier: {exc}"
            self.load_error_code = InferenceErrorCode.MODEL_FAILURE
            self.loading_status = ModelLoadingStatus.FAILED
            logger.error(self.last_error)
            return False

    def unload(self) -> None:
        """Unload model from RAM."""
        self._model = None
        self.loading_status = ModelLoadingStatus.UNLOADED
        self.active_device = None

    def predict(self, preprocessed_input: np.ndarray) -> np.ndarray:
        """
        Execute disease classification inference.
        Returns:
            np.ndarray of shape (1, 38) representing class probabilities.
        """
        if self.is_ready() and self._model is not None:
            import torch
            with torch.no_grad():
                tensor_in = torch.from_numpy(preprocessed_input).to(self.active_device)
                logits = self._model(tensor_in)
                probs = torch.softmax(logits, dim=-1).cpu().numpy()
                return probs

        raise RuntimeError(f"Model {self.name} is not loaded and failure behavior is {self.failure_behavior}")

    def predict_with_attention(
        self,
        preprocessed_input: np.ndarray,
        return_features: bool = False,
    ) -> Tuple[np.ndarray, np.ndarray] | Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return probabilities and residual-aware rollout across every backbone block."""
        if not self.is_ready() or self._model is None:
            raise RuntimeError(f"Model {self.name} is not loaded")
        import torch
        values = np.asarray(preprocessed_input)
        if (
            values.shape != (1, 3, 224, 224)
            or not np.issubdtype(values.dtype, np.floating)
            or not np.isfinite(values).all()
        ):
            raise ValueError("Attention rollout input must be finite float32 with shape (1, 3, 224, 224)")

        backbone = getattr(self._model, "backbone", None)
        blocks = getattr(backbone, "blocks", None)
        patch_size = getattr(backbone, "patch_size", None)
        if not blocks or not isinstance(patch_size, int) or patch_size <= 0:
            raise ValueError("Loaded classifier does not expose a supported DINOv2 transformer backbone")
        input_height, input_width = values.shape[-2:]
        if input_height % patch_size or input_width % patch_size:
            raise ValueError("Classifier input dimensions are not divisible by the DINOv2 patch size")
        grid_height = input_height // patch_size
        grid_width = input_width // patch_size
        expected_tokens = grid_height * grid_width + 1
        first_attention = getattr(blocks[0], "attn", None)
        head_count = getattr(first_attention, "num_heads", None)
        if not isinstance(head_count, int) or head_count <= 0:
            raise ValueError("Loaded DINOv2 attention block does not expose a valid head count")

        tensor_in = torch.from_numpy(values.astype(np.float32, copy=False)).to(self.active_device)
        with torch.inference_mode():
            logits, all_attns, feat = self._model(
                tensor_in, return_all_attentions=True, return_features=True
            )
            if (
                not isinstance(all_attns, (list, tuple))
                or len(all_attns) != len(blocks)
                or logits.shape != (1, 38)
                or feat.shape != (1, 768)
                or not torch.isfinite(logits).all()
                or not torch.isfinite(feat).all()
            ):
                raise ValueError("DINOv2 output does not match the loaded classifier architecture")

            rollout = None
            eye = torch.eye(expected_tokens, device=tensor_in.device)
            for attn in all_attns:
                if (
                    not isinstance(attn, torch.Tensor)
                    or attn.shape != (1, head_count, expected_tokens, expected_tokens)
                    or not torch.isfinite(attn).all()
                    or torch.any(attn < 0)
                ):
                    raise ValueError("DINOv2 block returned invalid attention tensors")
                mean_head = attn[0].mean(dim=0)
                residual_attention = mean_head + eye
                row_sums = residual_attention.sum(dim=-1, keepdim=True)
                if not torch.isfinite(row_sums).all() or torch.any(row_sums <= 0):
                    raise ValueError("DINOv2 attention rollout has invalid row sums")
                a_l = residual_attention / row_sums
                if rollout is None:
                    rollout = a_l
                else:
                    rollout = a_l @ rollout

            if rollout is None:
                raise ValueError("DINOv2 classifier returned no attention layers")
            cls_attn = rollout[0, 1:].reshape(1, 1, grid_height, grid_width)
            c_min, c_max = cls_attn.min(), cls_attn.max()
            if c_max > c_min:
                cls_attn = (cls_attn - c_min) / (c_max - c_min)
            else:
                cls_attn = torch.zeros_like(cls_attn)

            interpolated = torch.nn.functional.interpolate(
                cls_attn,
                size=(input_height, input_width),
                mode="bilinear",
                align_corners=False,
            )[0, 0]

            if not torch.isfinite(interpolated).all():
                raise ValueError("DINOv2 attention rollout contains non-finite values")

            probabilities = torch.softmax(logits, dim=-1).cpu().numpy()
            attention_map = interpolated.cpu().numpy().astype(np.float32)
            features = feat.cpu().numpy()[0]

        if return_features:
            return probabilities, attention_map, features
        return probabilities, attention_map

    def format_prediction(self, probabilities: np.ndarray, top_k: int = 5) -> Tuple[str, float, Dict[str, float], bool]:
        """
        Parse raw probabilities into primary class, confidence, top-k dict, and healthy flag.
        """
        probs_1d = probabilities[0] if probabilities.ndim == 2 else probabilities
        top_indices = np.argsort(probs_1d)[::-1][:top_k]

        primary_idx = int(top_indices[0])
        primary_class = self._class_names[primary_idx] if primary_idx < len(self._class_names) else f"Class_{primary_idx}"
        confidence = float(probs_1d[primary_idx])

        top_k_dict = {}
        for idx in top_indices:
            idx = int(idx)
            name = self._class_names[idx] if idx < len(self._class_names) else f"Class_{idx}"
            top_k_dict[name] = round(float(probs_1d[idx]), 4)

        is_healthy = "healthy" in primary_class.lower()
        return primary_class, round(confidence, 4), top_k_dict, is_healthy
