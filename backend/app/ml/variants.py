"""Deterministic, integrity-checked selection of immutable model variants."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.ml.errors import InferenceErrorCode, ModelCapabilityError


MODEL_IDS = {
    "sam2_instance_segmentation": "sam2_hiera_base_plus",
    "mobile_sam_instance_segmentation": "mobile_sam_vit_t",
    "dino_leaf_filter": "dinov2_vits14_leaf_filter",
    "dino_disease_classifier": "dinov2_vitb14_classifier",
    "segformer_disease_segmentation": "segformer_b0_plantseg",
}


class ModelVariantRegistry:
    """Reads manifest metadata and verifies the selected file before model load."""

    def __init__(self, root: Path, manifest_path: Path | None = None):
        self.root = root.resolve()
        self.manifest_path = manifest_path or self.root / "artifacts" / "model_manifest.json"
        try:
            self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelCapabilityError(InferenceErrorCode.MISSING_ARTIFACT,
                                       "Model variant manifest is missing or invalid", stage="variant_selection") from exc
        if self.manifest.get("schema_version") != "1.0.0" or not isinstance(self.manifest.get("models"), dict):
            raise ModelCapabilityError(InferenceErrorCode.INVALID_MODEL_OUTPUT,
                                       "Model variant manifest schema is unsupported", stage="variant_selection")
        self._verified: dict[tuple[str, int, int, str], bool] = {}

    def select(
        self,
        model_key: str,
        *,
        profile: str,
        capabilities: Any,
        memory_limit_gb: float | None = None,
        preference: str = "automatic",
        concurrency: int = 1,
    ) -> dict[str, Any]:
        model_id = MODEL_IDS.get(model_key)
        if model_id is None:
            raise ModelCapabilityError(InferenceErrorCode.UNSUPPORTED_RUNTIME,
                                       f"No variant registry entry for model '{model_key}'", stage="variant_selection")
        model = self.manifest["models"].get(model_id)
        if not model:
            raise ModelCapabilityError(InferenceErrorCode.MISSING_ARTIFACT,
                                       f"No variants registered for {model_id}", stage="variant_selection")
        profile = "cuda" if profile.startswith("cuda") else profile
        if preference not in {"automatic", "original"}:
            raise ValueError("Variant preference must be automatic or original")
        variants = sorted(model.get("variants", []), key=lambda v: self._selection_order(v, preference))
        compatibility_matrix = capabilities.model_compatibility.get(model_id, {})
        compatibility_entry = compatibility_matrix.get(profile, {})
        compatibility = compatibility_entry.get("status")
        available_runtimes = sorted(
            runtime for runtime, entry in compatibility_matrix.items()
            if runtime in {"cpu", "cuda", "mps"} and isinstance(entry, dict)
            and entry.get("status") == "prerequisites_present"
        )
        reasons: list[str] = []
        resource_rejected = False
        if compatibility != "prerequisites_present":
            unmet_requirements = self._runtime_rejection_reasons(
                model_id, compatibility_entry, capabilities
            )
            for variant in variants:
                profiles = ", ".join(variant.get("device_profiles", [])) or "none"
                reasons.append(
                    f"{variant.get('variant_id')}: requested profile '{profile}' "
                    f"is blocked; candidate profiles: {profiles}; unmet requirements: "
                    f"{', '.join(unmet_requirements)}"
                )
            tried = "; ".join(reasons) or "no eligible variants are registered"
            raise ModelCapabilityError(
                InferenceErrorCode.UNSUPPORTED_RUNTIME,
                f"No safe variant available for {model_id}: requested runtime '{profile}'; "
                f"available runtimes: {', '.join(available_runtimes) or 'none'}; "
                f"variants tried: {tried}",
                stage="variant_selection",
            )

        for variant in variants:
            optimized = variant.get("kind") != "original"
            if optimized:
                if variant.get("validation", {}).get("status") != "validated":
                    reasons.append(f"{variant.get('variant_id')}: validation is not approved")
                    continue
                if variant.get("benchmark", {}).get("compatibility_results", {}).get(profile) != "verified":
                    reasons.append(f"{variant.get('variant_id')}: runtime compatibility is not verified")
                    continue
            if profile not in variant.get("device_profiles", []):
                reasons.append(f"{variant.get('variant_id')}: profile not listed")
                continue
            benchmark = variant.get("benchmark", {})
            memory_metric = "vram_peak_gb" if profile == "cuda" else "ram_peak_gb"
            measured_peak = benchmark.get(memory_metric)
            if memory_limit_gb is not None and (measured_peak is None or measured_peak > memory_limit_gb):
                resource_rejected = True
                reasons.append(f"{variant.get('variant_id')}: no passing measured {memory_metric} under configured limit")
                continue
            concurrency_tested = benchmark.get("concurrency_results", {}).get(profile, 1)
            if concurrency > concurrency_tested:
                resource_rejected = True
                reasons.append(f"{variant.get('variant_id')}: concurrency {concurrency} exceeds tested limit {concurrency_tested}")
                continue
            artifact = self._verified_path(variant)
            if artifact is None:
                reasons.append(f"{variant.get('variant_id')}: missing artifact or SHA-256 mismatch/unavailable")
                continue

            def resolve_identity(key: str):
                identity = variant.get(key)
                return model.get(key) if identity == "same_as_model" else identity

            if (not self._verify_identity_file(resolve_identity("preprocessing_identity"))
                    or not self._verify_identity_file(resolve_identity("label_mapping_identity"))):
                reasons.append(f"{variant.get('variant_id')}: preprocessing or label mapping identity mismatch")
                continue

            return {"model_id": model_id, "variant_id": variant["variant_id"],
                    "kind": variant["kind"], "path": artifact, "backend": variant["backend"],
                    "precision": variant["precision"], "sha256": variant["sha256"],
                    "validation_status": variant.get("validation", {}).get("status"),
                    "preprocessing_identity": resolve_identity("preprocessing_identity"),
                    "label_mapping_identity": resolve_identity("label_mapping_identity"),
                    "source_checkpoint_identity": resolve_identity("source_checkpoint_identity")}

        reason = "; ".join(reasons) or "no eligible variants are registered"
        code = InferenceErrorCode.RESOURCE_LIMIT if resource_rejected else InferenceErrorCode.ARTIFACT_INTEGRITY
        raise ModelCapabilityError(code,
                                   f"No safe variant available for {model_id}: requested runtime '{profile}'; "
                                   f"available runtimes: {', '.join(available_runtimes) or 'none'}; "
                                   f"variants tried: {reason}", stage="variant_selection")

    @staticmethod
    def _runtime_rejection_reasons(
        model_id: str,
        compatibility: dict[str, Any],
        capabilities: Any,
    ) -> list[str]:
        requirements = compatibility.get("requirements", [])
        failed: list[str] = []
        if any(requirement.lower().startswith("python 3.12") for requirement in requirements):
            if not getattr(capabilities, "supported_python_version", True):
                failed.append(
                    f"Python 3.12 required (found {getattr(capabilities, 'python_version', 'unknown')})"
                )

        package_versions = getattr(capabilities, "packages", {})
        package_compatibility = getattr(capabilities, "package_version_compatibility", {})
        package_names = ("torch", "torchvision", "transformers", "safetensors", "sam2", "mobile_sam", "timm")
        for requirement in requirements:
            package = next(
                (name for name in package_names if requirement.lower().startswith(name)),
                None,
            )
            if package == "torch" and requirement.lower() == "torch":
                if not getattr(capabilities, "inference_backends", {}).get("torch", False):
                    failed.append("PyTorch is not installed")
            elif package and package_compatibility.get(package) is False:
                found = package_versions.get(package) or "not installed"
                failed.append(f"{requirement} required (found {package} {found})")

        model_compatibility = getattr(capabilities, "model_compatibility", {}).get(model_id, {})
        if (any("official_hiera_base_plus_config" in requirement for requirement in requirements)
                and model_compatibility.get("config_present") is False):
            failed.append("official Hiera Base Plus package config is unavailable")
        if (any("available_nvidia_cuda_device" in requirement for requirement in requirements)
                and getattr(capabilities, "cuda", {}).get("available") is not True):
            failed.append("an available NVIDIA CUDA device is required")
        if (any("available_mps_device" in requirement for requirement in requirements)
                and getattr(capabilities, "mps", {}).get("available") is not True):
            failed.append("an available MPS device is required")
        return failed or [f"runtime compatibility status is '{compatibility.get('status', 'unknown')}'"]

    @staticmethod
    def _selection_order(variant: dict[str, Any], preference: str = "automatic") -> tuple[int, float, str]:
        optimized_validated = variant.get("kind") != "original" and variant.get("validation", {}).get("status") == "validated"
        latency = variant.get("benchmark", {}).get("latency_ms")
        priority = (0 if variant.get("kind") == "original" else 1) if preference == "original" else (0 if optimized_validated else 1)
        return (priority,
                float(latency) if isinstance(latency, (int, float)) else float("inf"),
                str(variant.get("variant_id", "")))

    def _verified_path(self, variant: dict[str, Any]) -> Path | None:
        relative = variant.get("path")
        expected = variant.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            return None
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            return None
        stat = path.stat()
        key = (str(path), stat.st_size, stat.st_mtime_ns, expected.lower())
        if key not in self._verified:
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            self._verified[key] = digest.hexdigest().lower() == expected.lower()
        return path if self._verified[key] else None

    def _verify_identity_file(self, identity: Any) -> bool:
        if not isinstance(identity, dict):
            return True
        checks = []
        if identity.get("path"):
            checks.append((identity["path"], identity.get("sha256")))
        if identity.get("config_path"):
            checks.append((identity["config_path"], identity.get("config_sha256")))
        for relative, expected in checks:
            if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
                return False
            path = (self.root / relative).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():
                return False
            stat = path.stat()
            key = (str(path), stat.st_size, stat.st_mtime_ns, expected.lower())
            if key not in self._verified:
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                self._verified[key] = digest.hexdigest().lower() == expected.lower()
            if not self._verified[key]:
                return False
        return True
