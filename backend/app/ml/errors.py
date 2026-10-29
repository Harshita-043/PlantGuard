"""Stable, typed failures emitted by model inference."""

from enum import StrEnum


class InferenceErrorCode(StrEnum):
    MISSING_ARTIFACT = "missing_artifact"
    UNSUPPORTED_RUNTIME = "unsupported_runtime"
    INVALID_IMAGE = "invalid_image"
    INVALID_MODEL_OUTPUT = "invalid_model_output"
    ARTIFACT_INTEGRITY = "artifact_integrity"
    INVALID_CONFIGURATION = "invalid_configuration"
    OOD_CALIBRATION_UNAVAILABLE = "ood_calibration_unavailable"
    OUT_OF_DISTRIBUTION = "out_of_distribution"
    ARTIFACT_STORAGE_FAILURE = "artifact_storage_failure"
    RESOURCE_LIMIT = "resource_limit"
    REMOTE_FAILURE = "remote_failure"
    NO_LEAF_FOUND = "no_leaf_found"
    NO_DISEASE_MASK = "no_disease_mask"
    TIMEOUT = "timeout"
    MODEL_FAILURE = "model_failure"


class InferenceError(RuntimeError):
    """A request-safe model capability or inference failure."""

    def __init__(self, code: InferenceErrorCode, message: str, *, stage: str):
        super().__init__(message)
        self.code = code
        self.stage = stage


class ModelCapabilityError(InferenceError):
    """A model cannot execute because its artifact/runtime/config is unavailable."""


class InvalidImageError(InferenceError):
    def __init__(self, message: str):
        super().__init__(InferenceErrorCode.INVALID_IMAGE, message, stage="image_validation")


class NoLeafFoundError(InferenceError):
    def __init__(self, message: str = "SAM2 returned no valid leaf candidates"):
        super().__init__(InferenceErrorCode.NO_LEAF_FOUND, message, stage="leaf_filter")


class NoDiseaseMaskError(InferenceError):
    def __init__(self, message: str = "SegFormer returned no diseased pixels"):
        super().__init__(InferenceErrorCode.NO_DISEASE_MASK, message, stage="disease_segmentation")


class InferenceTimeoutError(InferenceError):
    def __init__(self, message: str = "Inference capacity was not available before timeout"):
        super().__init__(InferenceErrorCode.TIMEOUT, message, stage="pipeline")
