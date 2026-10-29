"""
DINOv2 Attention Rollout Explainer.

Implements attention rollout (Abnar & Zuidema, 2020) for Vision Transformers
to generate faithful input-saliency heatmaps across all 12 self-attention layers
of the DINOv2 Base disease classifier.

Loaded lazily on demand using the FP32 PyTorch model checkpoint.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import torch
    import torch.nn.functional as F
    from app.ml.architectures.dinov2 import build_dino_disease_classifier, DinoClassifierModel
except ImportError:
    torch = None
    F = None
    build_dino_disease_classifier = None
    DinoClassifierModel = None

logger = logging.getLogger(__name__)


class AttentionRolloutExplainer:
    """
    Computes explainability heatmaps using Attention Rollout across all 12 transformer layers.
    
    Tokens geometry for DINOv2 Base at 224x224:
      - Patch size: 14x14
      - Input resolution: 224x224
      - Patch grid: 16x16 = 256 patches
      - CLS tokens: 1
      - Register tokens: 0
      - Total tokens per layer: 257
    """

    METHOD_NAME: str = "dinov2_attention_rollout"

    def __init__(
        self,
        checkpoint_path: Optional[Union[str, Path]] = None,
        device: str = "cpu",
    ):
        self.device = device
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else self._default_checkpoint_path()
        self._model: Optional[DinoClassifierModel] = None

    def _default_checkpoint_path(self) -> Path:
        candidates = [
            Path("artifacts/dino_disease/dino_disease_classifier.pt"),
            Path("../artifacts/dino_disease/dino_disease_classifier.pt"),
            Path(__file__).resolve().parents[3] / "artifacts" / "dino_disease" / "dino_disease_classifier.pt",
        ]
        for c in candidates:
            if c.exists():
                return c.resolve()
        return Path("artifacts/dino_disease/dino_disease_classifier.pt")

    def _ensure_model_loaded(self) -> DinoClassifierModel:
        """Lazily load the FP32 PyTorch DINOv2 model into RAM."""
        if self._model is not None:
            return self._model

        if torch is None or build_dino_disease_classifier is None:
            raise RuntimeError("PyTorch runtime is not installed. Attention Rollout requires the ML runtime.")

        logger.info("Lazily loading FP32 PyTorch DINOv2 model for Attention Rollout from %s", self.checkpoint_path)
        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"DINOv2 checkpoint not found for explainability at {self.checkpoint_path}")

        model = build_dino_disease_classifier()
        checkpoint = torch.load(str(self.checkpoint_path), map_location=self.device)
        state_dict = checkpoint.get("state_dict", checkpoint)
        model.load_state_dict(state_dict, strict=True)
        model.to(self.device)
        model.eval()

        self._model = model
        return self._model

    def preprocess(self, image_rgb: np.ndarray, target_size: int = 224) -> torch.Tensor:
        """
        Preprocess image to normalized tensor (1, 3, 224, 224) using ImageNet mean/std.
        """
        pil_img = Image.fromarray(image_rgb).convert("RGB")
        resized = pil_img.resize((target_size, target_size), Image.Resampling.BILINEAR)
        arr = np.array(resized, dtype=np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        norm = (arr - mean) / std
        chw = np.transpose(norm, (2, 0, 1))
        tensor = torch.from_numpy(chw).unsqueeze(0).to(self.device)
        return tensor

    def compute_rollout_heatmap(
        self,
        crop_rgb: np.ndarray,
        discard_ratio: float = 0.0,
    ) -> np.ndarray:
        """
        Execute Attention Rollout through all 12 layers on the input crop.
        
        Returns:
            2D numpy array of shape (16, 16) normalized in [0, 1].
        """
        model = self._ensure_model_loaded()
        tensor_in = self.preprocess(crop_rgb)

        with torch.no_grad():
            _, attentions = model(tensor_in, return_all_attentions=True)

        if not attentions or len(attentions) != 12:
            raise ValueError(f"Expected 12 attention maps from DINOv2 Base, received {len(attentions) if attentions else 0}")

        # Attention Rollout algorithm across all 12 layers:
        # A_l = 0.5 * Attention_l + 0.5 * Identity
        rollout = None
        for attn in attentions:
            # attn shape: (1, 12_heads, 257, 257)
            # Average across attention heads
            A = attn.mean(dim=1)  # shape: (1, 257, 257)

            if discard_ratio > 0.0:
                flat = A.view(A.size(0), -1)
                val, _ = torch.topk(flat, int(flat.size(1) * discard_ratio), largest=False)
                threshold = val[:, -1].view(-1, 1, 1)
                A = torch.where(A < threshold, torch.zeros_like(A), A)

            # Account for residual skip connection (Identity matrix)
            I = torch.eye(A.size(-1), device=self.device).unsqueeze(0)
            A = 0.5 * A + 0.5 * I
            A = A / A.sum(dim=-1, keepdim=True)

            if rollout is None:
                rollout = A
            else:
                rollout = torch.bmm(A, rollout)

        # Token 0 is CLS token; tokens 1..256 are the 16x16 patch tokens
        cls_attention = rollout[0, 0, 1:].detach().cpu().numpy()
        
        if cls_attention.shape[0] != 256:
            raise ValueError(f"Expected 256 patch tokens, received {cls_attention.shape[0]}")

        heatmap = cls_attention.reshape(16, 16)
        
        # Normalize to [0, 1]
        h_min = heatmap.min()
        h_max = heatmap.max()
        if h_max > h_min:
            heatmap = (heatmap - h_min) / (h_max - h_min + 1e-8)
        else:
            heatmap = np.zeros_like(heatmap)

        return heatmap.astype(np.float32)

    def generate_crop_heatmap(
        self,
        crop_rgb: np.ndarray,
        target_shape: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Generate heatmap upscaled to match leaf crop dimensions (H, W).
        """
        heatmap_16x16 = self.compute_rollout_heatmap(crop_rgb)
        out_h, out_w = target_shape if target_shape else (crop_rgb.shape[0], crop_rgb.shape[1])
        
        # Bilinear interpolation to crop dimensions
        upscaled = cv2.resize(heatmap_16x16, (out_w, out_h), interpolation=cv2.INTER_LINEAR)
        return np.clip(upscaled, 0.0, 1.0).astype(np.float32)

    def create_overlay(
        self,
        image_rgb: np.ndarray,
        heatmap_2d: np.ndarray,
        alpha: float = 0.6,
        colormap: int = cv2.COLORMAP_JET,
    ) -> np.ndarray:
        """
        Blend a 2D float32 heatmap [0, 1] with an RGB image.
        Returns:
            RGB uint8 array of shape (H, W, 3).
        """
        if heatmap_2d.shape[:2] != image_rgb.shape[:2]:
            heatmap_2d = cv2.resize(heatmap_2d, (image_rgb.shape[1], image_rgb.shape[0]), interpolation=cv2.INTER_LINEAR)

        heatmap_uint8 = np.clip(heatmap_2d * 255.0, 0, 255).astype(np.uint8)
        heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, colormap)
        heatmap_color_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)

        overlay = (alpha * image_rgb.astype(np.float32) + (1.0 - alpha) * heatmap_color_rgb.astype(np.float32))
        return np.clip(overlay, 0, 255).astype(np.uint8)

    def map_to_original(
        self,
        original_rgb: np.ndarray,
        crop_heatmap: np.ndarray,
        bbox: Tuple[int, int, int, int],
        alpha: float = 0.6,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Map leaf crop heatmap back to full original image dimensions.
        
        Args:
            original_rgb: Full original image as RGB uint8 (H_orig, W_orig, 3).
            crop_heatmap: 2D float32 heatmap corresponding to the leaf crop.
            bbox: (ymin, xmin, ymax, xmax) pixel coordinates in original_rgb.
            alpha: Image blending factor.
            
        Returns:
            (full_heatmap, full_overlay):
              - full_heatmap: 2D float32 array (H_orig, W_orig) in [0, 1].
              - full_overlay: 3D uint8 array (H_orig, W_orig, 3).
        """
        h_orig, w_orig = original_rgb.shape[:2]
        ymin, xmin, ymax, xmax = bbox
        ymin = max(0, min(h_orig - 1, int(ymin)))
        ymax = max(ymin + 1, min(h_orig, int(ymax)))
        xmin = max(0, min(w_orig - 1, int(xmin)))
        xmax = max(xmin + 1, min(w_orig, int(xmax)))

        crop_h = ymax - ymin
        crop_w = xmax - xmin

        # Resize crop heatmap to exact crop box
        resized_crop_heatmap = cv2.resize(crop_heatmap, (crop_w, crop_h), interpolation=cv2.INTER_LINEAR)

        full_heatmap = np.zeros((h_orig, w_orig), dtype=np.float32)
        full_heatmap[ymin:ymax, xmin:xmax] = resized_crop_heatmap

        full_overlay = self.create_overlay(original_rgb, full_heatmap, alpha=alpha)
        return full_heatmap, full_overlay


# Singleton instance
attention_rollout_explainer = AttentionRolloutExplainer()
