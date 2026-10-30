from pathlib import Path
import hashlib
import json
from types import SimpleNamespace, MethodType

import pytest
import numpy as np

from app.api.admin import _authorized
from app.api.admin import runtime_diagnostics
from app.core.config import settings
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


def test_requested_model_version_includes_optimized_variant():
    variants = [
        _variant("v1-pytorch-fp32", model_version="v1"),
        _variant("v1-onnx-int8", "optimized", model_version="v1",
                 backend="onnxruntime-cpu",
                 validation={"status": "validated"},
                 benchmark={"latency_ms": 90.0, "ram_peak_gb": 2.0,
                            "compatibility_results": {"cpu": "verified"}}),
    ]
    capabilities = _caps()
    capabilities.inference_backends = {"onnxruntime": True}
    capabilities.package_version_compatibility = {"onnxruntime": True}
    registry = _registry(None, variants)

    result = registry.select(
        "dino_disease_classifier",
        profile="cpu",
        capabilities=capabilities,
        requested_variant="v1",
    )

    assert result["variant_id"] == "v1-onnx-int8"


def test_requested_model_version_falls_back_when_onnxruntime_is_missing():
    variants = [
        _variant("v1-pytorch-fp32", model_version="v1"),
        _variant("v1-onnx-int8", "optimized", model_version="v1",
                 backend="onnxruntime-cpu",
                 validation={"status": "validated"},
                 benchmark={"latency_ms": 90.0, "ram_peak_gb": 2.0,
                            "compatibility_results": {"cpu": "verified"}}),
    ]
    capabilities = _caps()
    capabilities.inference_backends = {"onnxruntime": False}
    capabilities.package_version_compatibility = {"onnxruntime": False}
    registry = _registry(None, variants)

    result = registry.select(
        "dino_disease_classifier",
        profile="cpu",
        capabilities=capabilities,
        requested_variant="v1",
    )

    assert result["variant_id"] == "v1-pytorch-fp32"


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


def test_explicit_variant_selection_uses_only_the_requested_variant():
    registry = _registry(None, [
        _variant("original-pytorch-fp32"),
        _variant("onnx-fp32", "optimized", validation={"status": "validated"},
                 benchmark={"latency_ms": 10.0, "ram_peak_gb": 2.0,
                            "compatibility_results": {"cpu": "verified"}}),
    ])

    result = registry.select(
        "dino_disease_classifier",
        profile="cpu",
        capabilities=_caps(),
        requested_variant="original-pytorch-fp32",
    )

    assert result["variant_id"] == "original-pytorch-fp32"


def test_unregistered_explicit_variant_fails_instead_of_falling_back():
    registry = _registry(None, [_variant("original-pytorch-fp32")])

    with pytest.raises(ModelCapabilityError) as exc:
        registry.select(
            "dino_disease_classifier",
            profile="cpu",
            capabilities=_caps(),
            requested_variant="onnx_fp32",
        )

    assert exc.value.code == InferenceErrorCode.MISSING_ARTIFACT
    assert "not registered" in str(exc.value)


def test_variant_selection_requires_profile_compatibility_and_budget_measurements():
    registry = _registry(None, [_variant()])
    with pytest.raises(ModelCapabilityError) as exc:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps("blocked"))
    assert exc.value.code == InferenceErrorCode.UNSUPPORTED_RUNTIME
    assert "requested runtime 'cpu'" in str(exc.value)
    assert "available runtimes: none" in str(exc.value)
    assert "original: requested profile 'cpu' is blocked" in str(exc.value)

    with pytest.raises(ModelCapabilityError):
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps(), memory_limit_gb=2.0)

    with pytest.raises(ModelCapabilityError) as concurrency_error:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps(), concurrency=2)
    assert concurrency_error.value.code == InferenceErrorCode.RESOURCE_LIMIT


def test_unsupported_runtime_error_reports_versions_and_all_candidate_rejections():
    registry = _registry(None, [
        _variant("cpu-original"),
        _variant("cuda-original", device_profiles=["cuda"]),
    ])
    capabilities = SimpleNamespace(
        model_compatibility={
            "dinov2_vitb14_classifier": {
                "cpu": {"status": "blocked", "requirements": ["Python 3.12", "torch==2.6.0"]},
                "cuda": {"status": "prerequisites_present"},
            },
        },
        supported_python_version=False,
        python_version="3.14.0",
        packages={"torch": "2.14.1"},
        package_version_compatibility={"torch": False},
    )

    with pytest.raises(ModelCapabilityError) as exc:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=capabilities)

    message = str(exc.value)
    assert exc.value.code == InferenceErrorCode.UNSUPPORTED_RUNTIME
    assert "requested runtime 'cpu'" in message
    assert "available runtimes: cuda" in message
    assert "Python 3.12 required (found 3.14.0)" in message
    assert "torch==2.6.0 required (found torch 2.14.1)" in message
    assert "cpu-original:" in message
    assert "cuda-original:" in message
    assert "candidate profiles: cuda" in message


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
    assert registry._verified_path(_variant(path="artifacts/dino_disease/classes.json", sha256=expected)) == path
    assert registry._verified_path(_variant(path="artifacts/dino_disease/classes.json", sha256="0" * 64)) is None


def test_variant_registry_rejects_lfs_pointer_even_when_pointer_hash_matches(tmp_path):
    artifact = tmp_path / "artifacts" / "model.pt"
    artifact.parent.mkdir()
    artifact.write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:" + ("a" * 64) + "\n"
        "size 1234\n",
        encoding="ascii",
    )
    variant = _variant(
        path="artifacts/model.pt",
        sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema_version": "1.0.0",
        "models": {"dinov2_vitb14_classifier": {"variants": [variant]}},
    }), encoding="utf-8")
    registry = ModelVariantRegistry(tmp_path, manifest_path=manifest_path)

    with pytest.raises(ModelCapabilityError) as exc:
        registry.select("dino_disease_classifier", profile="cpu", capabilities=_caps())

    assert exc.value.code is InferenceErrorCode.ARTIFACT_INTEGRITY
    assert "unhydrated Git LFS pointer" in str(exc.value)


def test_capability_report_does_not_treat_integrated_graphics_as_cuda_or_leak_paths():
    report = collect_runtime_capabilities(profile="cpu").public_dict()
    assert report["profile"] == "cpu"
    assert "model_compatibility" in report
    assert "remote" in report
    assert "token" not in str(report).lower()
    assert "C:\\Users" not in str(report)


def test_protected_runtime_diagnostics_report_safe_model_inventory(monkeypatch):
    from pydantic import SecretStr

    secret = "runtime-diagnostics-test-token"
    monkeypatch.setattr(settings, "PLANTGUARD_DIAGNOSTICS_TOKEN", SecretStr(secret))
    monkeypatch.setattr(settings, "PLANTGUARD_INFERENCE_PROFILE", "cpu")

    report = runtime_diagnostics(authorization=f"Bearer {secret}")
    model = report["model_variants"]["sam2_hiera_base_plus"]

    assert report["secrets_included"] is False
    assert model["initialization_status"] == "unloaded"
    assert model["loaded_model_identity"] is None
    assert model["device"] is None
    assert model["artifact_status"] in {"verified", "unavailable"}
    assert isinstance(model["supported_operations"], list)
    assert secret not in json.dumps(report)
    assert "C:\\Users" not in json.dumps(report)


def test_manifest_registers_originals_and_validated_optimized_variants():
    root = Path(__file__).resolve().parents[3]
    data = json.loads((root / "artifacts" / "model_manifest.json").read_text(encoding="utf-8"))
    assert set(data["models"]) == {
        "sam2_hiera_base_plus", "dinov2_vits14_leaf_filter",
        "dinov2_vitb14_classifier", "segformer_b0_plantseg", "mobile_sam_vit_t",
    }
    for model in data["models"].values():
        assert model["original_checkpoint"]["path"]
        assert any(variant["kind"] == "original" for variant in model["variants"])
    leaf_filter = data["models"]["dinov2_vits14_leaf_filter"]
    assert leaf_filter["original_checkpoint"]["path"] == "artifacts/dino_leaf_filter/dino_leaf_filter.pt"
    assert {variant["variant_id"] for variant in leaf_filter["variants"]} == {
        "v1-pytorch-fp32", "v2-pytorch-fp32", "v1-onnx-int8",
    }
    classifier = data["models"]["dinov2_vitb14_classifier"]
    assert {variant["variant_id"] for variant in classifier["variants"]} == {
        "original-pytorch-fp32", "onnx-fp32",
    }
    classifier_onnx = next(variant for variant in classifier["variants"] if variant["variant_id"] == "onnx-fp32")
    assert classifier_onnx["validation"]["status"] == "rejected_parity_mismatch"
    segformer = data["models"]["segformer_b0_plantseg"]
    assert {variant["variant_id"] for variant in segformer["variants"]} == {
        "original-transformers-fp32", "onnx-int8",
    }
    for model in data["models"].values():
        for variant in model["variants"]:
            if variant["kind"] != "original" and variant["validation"]["status"] != "rejected_parity_mismatch":
                assert variant["validation"]["status"] == "validated"


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
