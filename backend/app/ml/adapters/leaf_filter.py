"""
DINOv2 Small Leaf Filter Model Adapter.

Classifies image crops into binary leaf / non-leaf candidates before
passing them down the disease diagnosis pipeline.
Artifact: `artifacts/dino_leaf_filter/dino_leaf_filter.pt` (v1), with an
optional validated ONNX Runtime INT8 variant.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
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


class DinoLeafFilterAdapter(BaseModelAdapter):
    """
    Adapter for DINOv2 Small binary leaf filter.
    Backbone: dinov2_vits14 (embed_dim=384, depth=12, num_heads=6).
    Classification Head: LayerNorm(384) -> Linear(384, 1) -> Sigmoid.
    Target resolution: 224x224 RGB.
    Output: 2-class probabilities [prob_negative, prob_positive].
    """

    def __init__(
        self,
        artifact_path: Optional[Path] = None,
        artifact_version: str = "v1",
        failure_behavior: FailureBehavior = FailureBehavior.FAIL_FAST,
    ):
        path = artifact_path or self._resolve_default_path()
        super().__init__(
            name="dino_leaf_filter",
            artifact_path=path,
            artifact_version=artifact_version,
            device_requirements="cpu",
            failure_behavior=failure_behavior,
            evaluation_status=EvaluationStatus.UNTESTED,
        )
        self._model = None
        self._onnx_session = None
        self._onnx_input_name = None
        self._onnx_output_name = None
        self.execution_backend = "pytorch-native-dinov2"
        self._class_mapping = {0: "negative", 1: "positive"}

    def _resolve_default_path(self) -> Path:
        """Resolve path to leaf filter weights prioritizing v1."""
        candidates = [
            Path("artifacts/dino_leaf_filter/dino_leaf_filter.pt"),
            Path("artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt"),
            Path("../artifacts/dino_leaf_filter/dino_leaf_filter.pt"),
            Path("../artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("artifacts/dino_leaf_filter/dino_leaf_filter.pt")

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
            shape=(1, 2),
            description="Softmax/Sigmoid probability distribution over [negative, positive]",
        )

    def get_class_mapping(self) -> Optional[Dict[int, str]]:
        return self._class_mapping

    def load(self, target_device: str = "cpu") -> bool:
        """Load DINOv2 Small model weights into memory."""
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
            if self.execution_backend == "onnxruntime-cpu":
                import onnxruntime as ort

                if target_device != "cpu":
                    raise ValueError("The ONNX Runtime INT8 leaf filter supports CPU inference only")
                session = ort.InferenceSession(
                    str(self.artifact_path),
                    providers=["CPUExecutionProvider"],
                )
                inputs = session.get_inputs()
                outputs = session.get_outputs()
                if (
                    session.get_providers() != ["CPUExecutionProvider"]
                    or len(inputs) != 1
                    or inputs[0].name != "pixel_values"
                    or inputs[0].shape != [1, 3, 224, 224]
                    or inputs[0].type != "tensor(float)"
                    or len(outputs) != 1
                    or outputs[0].name != "logits"
                    or outputs[0].shape != [1]
                    or outputs[0].type != "tensor(float)"
                ):
                    raise ValueError("ONNX leaf filter does not match the configured input/output contract")
                self._onnx_session = session
                self._onnx_input_name = inputs[0].name
                self._onnx_output_name = outputs[0].name
                self.active_device = "cpu"
            elif self.execution_backend == "pytorch-native-dinov2":
                import torch
                from app.ml.architectures.dinov2 import build_dino_leaf_filter

                logger.info("Constructing DINOv2 Small model for %s...", self.artifact_path)
                model = build_dino_leaf_filter()
                checkpoint = torch.load(str(self.artifact_path), map_location=target_device, weights_only=True)

                state_dict = checkpoint.get("state_dict", checkpoint)
                model.load_state_dict(state_dict, strict=True)
                model.to(target_device)
                model.eval()
                self._model = model
            else:
                raise ValueError(f"Unsupported DINOv2 leaf-filter backend: {self.execution_backend}")

            self.loading_status = ModelLoadingStatus.READY
            logger.info("DINOv2 leaf filter loaded successfully with backend %s", self.execution_backend)
            return True
        except ImportError as e:
            self.last_error = f"Inference runtime import failed: {e}"
            self.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False
        except Exception as exc:
            self.last_error = f"Failed to load DINOv2 leaf filter: {exc}"
            self.load_error_code = InferenceErrorCode.MODEL_FAILURE
            self.loading_status = ModelLoadingStatus.FAILED
            logger.error(self.last_error)
            return False

    def unload(self) -> None:
        """Unload model from RAM."""
        self._model = None
        self._onnx_session = None
        self._onnx_input_name = None
        self._onnx_output_name = None
        self.loading_status = ModelLoadingStatus.UNLOADED
        self.active_device = None

    def predict(self, preprocessed_input: np.ndarray) -> np.ndarray:
        """
        Execute leaf filtering inference.
        Returns:
            np.ndarray of shape (1, 2) representing [prob_negative, prob_positive].
        """
        if self.is_ready() and self._onnx_session is not None:
            values = np.asarray(preprocessed_input)
            if (
                values.shape != (1, 3, 224, 224)
                or values.dtype != np.float32
                or not np.isfinite(values).all()
            ):
                raise ValueError("Leaf-filter input must be finite float32 with shape (1, 3, 224, 224)")
            logits = np.asarray(
                self._onnx_session.run(
                    [self._onnx_output_name],
                    {self._onnx_input_name: values},
                )[0],
                dtype=np.float32,
            )
            if logits.shape != (1,) or not np.isfinite(logits).all():
                raise ValueError("ONNX leaf filter returned invalid logits")
            probability_positive = 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))
            return np.stack((1.0 - probability_positive, probability_positive), axis=1).astype(np.float32)

        if self.is_ready() and self._model is not None:
            import torch
            with torch.no_grad():
                tensor_in = torch.from_numpy(preprocessed_input).to(self.active_device)
                logit = self._model(tensor_in)
                prob_positive = float(torch.sigmoid(logit).item())
                prob_negative = max(0.0, 1.0 - prob_positive)
                return np.array([[prob_negative, prob_positive]], dtype=np.float32)

        raise RuntimeError(f"Model {self.name} is not loaded and failure behavior is {self.failure_behavior}")
