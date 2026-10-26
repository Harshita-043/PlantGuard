from pathlib import Path
import hashlib
import json
from types import SimpleNamespace, MethodType

import pytest
import numpy as np

from app.api.admin import _authorized
from app.ml.device import DeviceManager
from app.ml.errors import InferenceErrorCode, ModelCapabilityError
from app.ml.remote import RemoteInferenceClient, validate_remote_base_url
from app.ml.runtime import collect_runtime_capabilities
from app.ml.variants import ModelVariantRegistry


def _registry(monkeypatch, variants):
    registry = object.__new__(ModelVariantRegistry)
    registry.root = Path.cwd().resolve()
    registry.manifest = {"schema_version": "1.0.0", "models": {
        "dinov2_vitb14_classifier": {"variants": variants},
    }}
    registry._verified = {}
    registry._verified_path = MethodType(lambda self, variant: Path("verified-checkpoint"), registry)
    return registry


def _caps(status="prerequisites_present"):
    return SimpleNamespace(model_compatibility={"dinov2_vitb14_classifier": {"cpu": {"status": status}}})


def _variant(variant_id="original", kind="original", **overrides):
    data = {
        "variant_id": variant_id, "kind": kind, "path": "artifacts/model.pt",
        "sha256": "a" * 64, "backend": "pytorch-native-dinov2", "precision": "fp32",
        "device_profiles": ["cpu"], "validation": {"status": "not_evaluated"},
        "benchmark": {"latency_ms": None, "ram_peak_gb": 3.0,
                      "compatibility_results": {"cpu": "verified"}},
    }
    data.update(overrides)
    return data


def test_variant_selection_prefers_verified_optimized_variant_deterministically():
    variants = [
        _variant("original"),
        _variant("int8", "optimized", validation={"status": "validated"},
                 benchmark={"latency_ms": 10.0, "ram_peak_gb": 2.0,
                            "compatibility_results": {"cpu": "verified"}}),
    ]
    registry = _registry(None, variants)
    result = registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps())
    assert result["variant_id"] == "int8"
    assert result["path"] == Path("verified-checkpoint")


def test_variant_selection_never_uses_unvalidated_optimized_variant():
    registry = _registry(None, [
        _variant("unvalidated-int8", "optimized"),
        _variant("original"),
    ])
    result = registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps())
    assert result["variant_id"] == "original"


def test_baseline_preference_selects_original_even_if_optimized_is_validated():
    registry = _registry(None, [
        _variant("int8", "optimized", validation={"status": "validated"},
                 benchmark={"latency_ms": 10.0, "ram_peak_gb": 2.0,
                            "compatibility_results": {"cpu": "verified"}}),
        _variant("original"),
    ])
    result = registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps(), preference="original")
    assert result["variant_id"] == "original"


def test_variant_selection_requires_profile_compatibility_and_budget_measurements():
    registry = _registry(None, [_variant()])
    with pytest.raises(ModelCapabilityError) as exc:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps("blocked"))
    assert exc.value.code == InferenceErrorCode.UNSUPPORTED_RUNTIME

    with pytest.raises(ModelCapabilityError):
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps(), memory_limit_gb=2.0)

    with pytest.raises(ModelCapabilityError) as concurrency_error:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps(), concurrency=2)
    assert concurrency_error.value.code == InferenceErrorCode.RESOURCE_LIMIT


def test_variant_registry_rejects_missing_sha256():
    registry = object.__new__(ModelVariantRegistry)
    registry.root = Path.cwd().resolve()
    assert registry._verified_path(_variant(sha256=None)) is None


def test_variant_registry_verifies_hash_without_loading_checkpoint_tensors():
    root = Path(__file__).resolve().parents[3]
    path = root / "artifacts" / "dino_disease" / "classes.json"
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    registry = object.__new__(ModelVariantRegistry)
    registry.root = root
    registry._verified = {}
    assert registry._verified_path(_variant(path="artifacts/dino_disease/classes.json", sha256=expected)) == path
    assert registry._verified_path(_variant(path="artifacts/dino_disease/classes.json", sha256="0" * 64)) is None


def test_capability_report_does_not_treat_integrated_graphics_as_cuda_or_leak_paths():
    report = collect_runtime_capabilities(profile="cpu").public_dict()
    assert report["profile"] == "cpu"
    assert "model_compatibility" in report
    assert "remote" in report
    assert "token" not in str(report).lower()
    assert "C:\\Users" not in str(report)


def test_manifest_registers_each_original_and_has_no_approved_optimized_variant():
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / "artifacts" / "model_manifest.json").read_text(encoding="utf-8"))
    assert set(data["models"]) == {
        "sam2_hiera_base_plus", "dinov2_vits14_leaf_filter",
        "dinov2_vitb14_classifier", "segformer_b0_plantseg",
    }
    for model in data["models"].values():
        assert model["original_checkpoint"]["path"]
        assert any(variant["kind"] == "original" for variant in model["variants"])
        assert not any(variant["kind"] != "original" and variant["validation"]["status"] == "validated"
                       for variant in model["variants"])


def test_explicit_cuda_request_is_not_silently_changed_to_cpu():
    assert DeviceManager(preferred_device="cuda").active_device == "cuda:0"


@pytest.mark.parametrize("url", ["http://example.com", "https://user:pass@example.com", "https://example.com/path", "https://example.com/?x=1"])
def test_remote_profile_rejects_unsafe_or_ambiguous_urls(url):
    with pytest.raises(ValueError):
        validate_remote_base_url(url)


def test_remote_profile_requires_https_and_valid_origin():
    assert validate_remote_base_url("https://inference.example/") == "https://inference.example"


def test_remote_client_requires_explicit_deployment_authorization():
    with pytest.raises(ModelCapabilityError):
        RemoteInferenceClient(base_url="https://inference.example", token="test-token")
    client = RemoteInferenceClient(base_url="https://inference.example", token="test-token",
                                   deployment_authorized=True)
    assert client.base_url == "https://inference.example"


def test_remote_client_enforces_image_dimensions_and_payload_cap_before_network():
    from app.ml.errors import InvalidImageError

    client = RemoteInferenceClient(base_url="https://inference.example", token="test-token",
                                   max_image_bytes=1, deployment_authorized=True)
    with pytest.raises(InvalidImageError):
        client.analyze(np.zeros((1, 1, 3), dtype=np.uint8))
    with pytest.raises(InvalidImageError):
        client.analyze(np.zeros((8193, 1, 3), dtype=np.uint8))


def test_diagnostics_auth_uses_only_configured_bearer_secret():
    assert _authorized("Bearer configured", "configured")
    assert not _authorized("Bearer wrong", "configured")
    assert not _authorized("Bearer configured", None)
