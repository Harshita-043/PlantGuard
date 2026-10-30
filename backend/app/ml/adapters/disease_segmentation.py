"""
SegFormer-B0 PlantSeg Disease Segmentation Model Adapter.

Computes semantic segmentation of plant leaf lesions from the SegFormer-B0
checkpoint trained on PlantSeg.
Artifact: `outputs/segformer_plantseg/best_model/model.safetensors`.
Config: `outputs/segformer_plantseg/best_model/config.json`.
Preprocessing: `outputs/segformer_plantseg/best_model/preprocessing.json`.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import numpy as np
from PIL import Image
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


class SegFormerDiseaseSegmentationAdapter(BaseModelAdapter):
    """
    Adapter for SegFormer-B0 (nvidia/mit-b0 backbone + MLP decoder) binary disease segmentation.
    Target resolution: 512x512 RGB.
    Output: 2-class logits / binary mask (0: background, 1: diseased_region).
    """

    def __init__(
        self,
        artifact_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        artifact_version: str = "plantseg-b0-v1",
        failure_behavior: FailureBehavior = FailureBehavior.FAIL_FAST,
    ):
        path = artifact_path or self._resolve_default_path()
        super().__init__(
            name="segformer_disease_segmentation",
            artifact_path=path,
            artifact_version=artifact_version,
            device_requirements="cpu",
            failure_behavior=failure_behavior,
            evaluation_status=EvaluationStatus.UNTESTED,
        )
        self.config_path = config_path or (self.artifact_path.parent / "config.json")
        self.preprocessing_path = self.artifact_path.parent / "preprocessing.json"
        self._model = None
        self._onnx_session = None
        self._onnx_input_name = None
        self._onnx_output_name = None
        self.execution_backend = "pytorch-transformers"
        self._class_mapping = {0: "background", 1: "diseased_region"}
        self._target_size = (512, 512)
        self._mean = (0.485, 0.456, 0.406)
        self._std = (0.229, 0.224, 0.225)
        self._configuration_error: Optional[str] = None
        self._load_config_and_preprocessing()

    def _resolve_default_path(self) -> Path:
        candidates = [
            Path("outputs/segformer_plantseg/best_model/model.safetensors"),
            Path("../outputs/segformer_plantseg/best_model/model.safetensors"),
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("outputs/segformer_plantseg/best_model/model.safetensors")

    def _load_config_and_preprocessing(self) -> None:
        try:
            if not self.config_path.is_file() or not self.preprocessing_path.is_file():
                raise FileNotFoundError("SegFormer config.json and preprocessing.json are both required")
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if "id2label" not in cfg or "label2id" not in cfg:
                raise ValueError("SegFormer config must include id2label and label2id")
            id2label = {int(k): str(v) for k, v in cfg["id2label"].items()}
            label2id = {str(k): int(v) for k, v in cfg["label2id"].items()}
            expected = {0: "background", 1: "diseased_region"}
            if id2label != expected or label2id != {v: k for k, v in expected.items()}:
                raise ValueError("SegFormer mappings do not match the PlantSeg checkpoint labels")
            self._class_mapping = id2label
            with open(self.preprocessing_path, "r", encoding="utf-8") as f:
                pre = json.load(f)
            size = pre.get("size")
            if not isinstance(size, int) or size <= 0:
                raise ValueError("SegFormer preprocessing size must be a positive integer")
            self._target_size = (size, size)
            self._mean = tuple(float(v) for v in pre.get("mean", self._mean))
            self._std = tuple(float(v) for v in pre.get("std", self._std))
            if len(self._mean) != 3 or len(self._std) != 3 or not np.isfinite(self._mean).all() or not np.isfinite(self._std).all() or any(v <= 0 for v in self._std):
                raise ValueError("SegFormer normalization must contain three finite means and positive standard deviations")
            if pre.get("class_mapping") is not None:
                mapping = {int(k): str(v) for k, v in pre["class_mapping"].items()}
                if mapping != self._class_mapping:
                    raise ValueError("SegFormer preprocessing mapping does not match config")
        except Exception as e:
            self._configuration_error = str(e)
            logger.warning("SegFormer configuration is invalid: %s", e)

    def get_input_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="np.ndarray[float32]",
            shape=(1, 3, self._target_size[0], self._target_size[1]),
            description=f"Normalized RGB tensor CHW format ({self._target_size[0]}x{self._target_size[1]})",
        )

    def get_preprocessing_spec(self) -> PreprocessingSpec:
        return PreprocessingSpec(
            target_size=self._target_size,
            mean=self._mean,
            std=self._std,
            color_mode="RGB",
            normalization_range=(0.0, 1.0),
        )

    def get_output_contract(self) -> ContractSpec:
        return ContractSpec(
            data_type="np.ndarray[uint8]",
            shape=self._target_size,
            description="Binary segmentation mask (0: background, 1: diseased_region)",
        )

    def get_class_mapping(self) -> Optional[Dict[int, str]]:
        return self._class_mapping

    def load(self, target_device: str = "cpu") -> bool:
        """Load SegFormer safetensors weights locally into memory."""
        self.loading_status = ModelLoadingStatus.LOADING
        self.active_device = target_device
        self.last_error = None
        self.load_error_code = None

        if self._configuration_error:
            self.last_error = f"Invalid SegFormer configuration: {self._configuration_error}"
            self.load_error_code = InferenceErrorCode.INVALID_CONFIGURATION
            self.loading_status = ModelLoadingStatus.FAILED
            return False

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
                    raise ValueError("The ONNX Runtime SegFormer INT8 variant supports CPU inference only")
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
                    or inputs[0].shape != [1, 3, 512, 512]
                    or inputs[0].type != "tensor(float)"
                    or len(outputs) != 1
                    or outputs[0].name != "logits"
                    or outputs[0].shape != [1, 2, 512, 512]
                    or outputs[0].type != "tensor(float)"
                ):
                    raise ValueError("ONNX SegFormer does not match the PlantSeg input/output contract")
                self._onnx_session = session
                self._onnx_input_name = inputs[0].name
                self._onnx_output_name = outputs[0].name
                self.active_device = "cpu"
            elif self.execution_backend == "pytorch-transformers":
                from transformers import SegformerForSemanticSegmentation
                model_dir = str(self.artifact_path.parent)
                logger.info("Loading local SegFormer-B0 from %s onto %s (local_files_only=True)...", model_dir, target_device)

                model = SegformerForSemanticSegmentation.from_pretrained(
                    model_dir,
                    local_files_only=True,
                )
                model.to(target_device)
                model.eval()
                self._model = model
            else:
                raise ValueError(f"Unsupported SegFormer backend: {self.execution_backend}")
            self.loading_status = ModelLoadingStatus.READY
            logger.info("SegFormer-B0 loaded with backend %s", self.execution_backend)
            return True
        except ImportError as e:
            self.last_error = f"Inference runtime import failed: {e}"
            self.load_error_code = InferenceErrorCode.UNSUPPORTED_RUNTIME
            self.loading_status = ModelLoadingStatus.FAILED
            logger.warning(self.last_error)
            return False
        except Exception as exc:
            self.last_error = f"Failed to load SegFormer safetensors: {exc}"
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

    def predict(self, preprocessed_input: np.ndarray, original_shape: Optional[Tuple[int, int]] = None) -> np.ndarray:
        """
        Execute segmentation forward pass and upsample logits to target shape.

        Args:
            preprocessed_input: CHW float32 array (1, 3, 512, 512).
            original_shape: Optional (height, width) to upsample logits to match original image.

        Returns:
            np.ndarray uint8 binary mask (0 or 1).
        """
        target_h, target_w = original_shape or self._target_size

        if self.is_ready() and self._onnx_session is not None:
            values = np.asarray(preprocessed_input)
            if (
                values.shape != (1, 3, 512, 512)
                or values.dtype != np.float32
                or not np.isfinite(values).all()
            ):
                raise ValueError("SegFormer input must be finite float32 with shape (1, 3, 512, 512)")
            if target_h <= 0 or target_w <= 0:
                raise ValueError("SegFormer output dimensions must be positive")
            logits = np.asarray(
                self._onnx_session.run(
                    [self._onnx_output_name],
                    {self._onnx_input_name: values},
                )[0],
                dtype=np.float32,
            )
            if logits.shape != (1, 2, 512, 512) or not np.isfinite(logits).all():
                raise ValueError("ONNX SegFormer returned invalid PlantSeg logits")
            import torch
            with torch.inference_mode():
                tensor_logits = torch.from_numpy(logits)
                resized_logits = torch.nn.functional.interpolate(
                    tensor_logits,
                    size=(target_h, target_w),
                    mode="bilinear",
                    align_corners=False,
                )
                return torch.argmax(resized_logits, dim=1).squeeze(0).numpy().astype(np.uint8)

        if self.is_ready() and self._model is not None:
            import torch
            with torch.no_grad():
                tensor_in = torch.from_numpy(preprocessed_input).to(self.active_device)
                outputs = self._model(pixel_values=tensor_in)
                logits = outputs.logits  # shape: (1, 2, 128, 128)
                if (not isinstance(logits, torch.Tensor) or logits.ndim != 4 or logits.shape[0] != 1
                        or logits.shape[1] != len(self._class_mapping) or not torch.isfinite(logits).all()):
                    raise RuntimeError("SegFormer logits must be finite with shape (1, mapped_classes, h, w)")
                if target_h <= 0 or target_w <= 0:
                    raise ValueError("SegFormer output dimensions must be positive")

                # Bilinearly interpolate logits directly to the target shape
                upsampled = torch.nn.functional.interpolate(
                    logits,
                    size=(target_h, target_w),
                    mode="bilinear",
                    align_corners=False,
                )
                pred_mask = torch.argmax(upsampled, dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
                return pred_mask

        raise RuntimeError(f"Model {self.name} is not loaded and failure behavior is {self.failure_behavior}")
