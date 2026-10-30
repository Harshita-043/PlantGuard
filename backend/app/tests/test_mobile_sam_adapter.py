import pickle
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from app.ml.adapters.mobile_sam_adapter import MobileSamLeafSegmentationAdapter
from app.ml.errors import InferenceErrorCode
from app.ml.interfaces.adapter import ModelLoadingStatus


class _Tensor:
    def __init__(self, shape):
        self.shape = shape


class _MobileSamModel:
    def __init__(self):
        self.loaded_state_dict = None
        self.device = None
        self.evaluated = False

    def state_dict(self):
        return {"encoder.weight": _Tensor((2, 3))}

    def load_state_dict(self, state_dict, *, strict):
        assert strict is True
        self.loaded_state_dict = state_dict

    def to(self, *, device):
        self.device = device
        return self

    def eval(self):
        self.evaluated = True
        return self


def _install_mobile_sam_mocks(monkeypatch, state_dict=None, load_error=None):
    calls = {}
    model = _MobileSamModel()

    torch = ModuleType("torch")
    torch.cuda = SimpleNamespace(is_available=lambda: False)
    torch.backends = SimpleNamespace(mps=SimpleNamespace(is_available=lambda: False))

    def load(path, *, map_location, weights_only):
        calls["load"] = (path, map_location, weights_only)
        if load_error:
            raise load_error
        return state_dict or {"encoder.weight": _Tensor((2, 3))}

    torch.load = load
    torch.is_tensor = lambda value: isinstance(value, _Tensor)
    mobile_sam = ModuleType("mobile_sam")
    mobile_sam.SamPredictor = lambda loaded_model: ("predictor", loaded_model)
    mobile_sam.sam_model_registry = {
        "vit_t": lambda *, checkpoint: calls.setdefault("constructor_checkpoint", checkpoint) or model
    }

    monkeypatch.setitem(__import__("sys").modules, "torch", torch)
    monkeypatch.setitem(__import__("sys").modules, "mobile_sam", mobile_sam)
    return calls, model


def test_mobile_sam_loads_cpu_state_dict_with_explicit_safe_deserialization(tmp_path, monkeypatch):
    checkpoint = tmp_path / "mobile_sam.pt"
    checkpoint.write_bytes(b"fixture checkpoint")
    state_dict = {"encoder.weight": _Tensor((2, 3))}
    calls, model = _install_mobile_sam_mocks(monkeypatch, state_dict=state_dict)
    adapter = MobileSamLeafSegmentationAdapter(artifact_path=checkpoint)

    assert adapter.load("cpu") is True
    assert calls["load"] == (str(checkpoint), "cpu", True)
    assert calls["constructor_checkpoint"] is None
    assert model.loaded_state_dict is state_dict
    assert model.device == "cpu"
    assert model.evaluated
    assert adapter.is_ready()
    assert adapter.loading_status is ModelLoadingStatus.READY


def test_mobile_sam_missing_checkpoint_is_reported_without_loading(tmp_path):
    adapter = MobileSamLeafSegmentationAdapter(artifact_path=tmp_path / "missing.pt")

    assert adapter.load("cpu") is False
    assert adapter.loading_status is ModelLoadingStatus.FAILED
    assert adapter.load_error_code is InferenceErrorCode.MISSING_ARTIFACT


def test_mobile_sam_corrupt_checkpoint_fails_closed(tmp_path, monkeypatch):
    checkpoint = tmp_path / "corrupt.pt"
    checkpoint.write_bytes(b"corrupt")
    _install_mobile_sam_mocks(
        monkeypatch,
        load_error=pickle.UnpicklingError("invalid checkpoint data"),
    )
    adapter = MobileSamLeafSegmentationAdapter(artifact_path=checkpoint)

    assert adapter.load("cpu") is False
    assert adapter.loading_status is ModelLoadingStatus.FAILED
    assert adapter.load_error_code is InferenceErrorCode.ARTIFACT_INTEGRITY
    assert "UnpicklingError" in adapter.last_error


@pytest.mark.parametrize(
    "state_dict, mismatch",
    [
        ({"different.weight": _Tensor((2, 3))}, "missing="),
        ({"encoder.weight": _Tensor((3, 2))}, "shape_mismatches="),
    ],
)
def test_mobile_sam_rejects_incompatible_state_dict(
    tmp_path: Path,
    monkeypatch,
    state_dict,
    mismatch,
):
    checkpoint = tmp_path / "incompatible.pt"
    checkpoint.write_bytes(b"fixture checkpoint")
    _install_mobile_sam_mocks(monkeypatch, state_dict=state_dict)
    adapter = MobileSamLeafSegmentationAdapter(artifact_path=checkpoint)

    assert adapter.load("cpu") is False
    assert adapter.loading_status is ModelLoadingStatus.FAILED
    assert adapter.load_error_code is InferenceErrorCode.MODEL_FAILURE
    assert mismatch in adapter.last_error

