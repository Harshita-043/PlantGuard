import os
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml.cam import AttentionRolloutExplainer

image_path = "apple-scab-disease-stockcake.jpg"
if not os.path.exists(image_path):
    print("Error: Image not found:", image_path)
    sys.exit(1)

# Load real image
orig_img = Image.open(image_path).convert("RGB")
orig_np = np.array(orig_img)
orig_h, orig_w = orig_np.shape[:2]
print(f"Loaded original image: {image_path} (Shape: {orig_np.shape})")

# Simulate a leaf crop or take center crop / full image
# In PlantGuard pipeline, a detected leaf bbox [ymin, xmin, ymax, xmax] is cropped
ymin, xmin = int(0.15 * orig_h), int(0.15 * orig_w)
ymax, xmax = int(0.85 * orig_h), int(0.85 * orig_w)
crop_np = orig_np[ymin:ymax, xmin:xmax]
print(f"Crop shape: {crop_np.shape} from bbox: {(ymin, xmin, ymax, xmax)}")

explainer = AttentionRolloutExplainer()
print(f"Explainer initialized with method: {explainer.METHOD_NAME}")

# 1. 16x16 attention rollout heatmap
heatmap_16x16 = explainer.compute_rollout_heatmap(crop_np)
print(f"16x16 Heatmap shape: {heatmap_16x16.shape}, dtype: {heatmap_16x16.dtype}")
print(f"Heatmap value range: min={heatmap_16x16.min():.4f}, max={heatmap_16x16.max():.4f}, mean={heatmap_16x16.mean():.4f}")

# 2. Crop heatmap upscaled to crop dimensions
crop_heatmap = explainer.generate_crop_heatmap(crop_np)
print(f"Crop Heatmap shape: {crop_heatmap.shape}, dtype: {crop_heatmap.dtype}")

# 3. Crop overlay
crop_overlay = explainer.create_overlay(crop_np, crop_heatmap)
print(f"Crop Overlay shape: {crop_overlay.shape}")

# 4. Map back to original image
full_heatmap, full_overlay = explainer.map_to_original(orig_np, crop_heatmap, (ymin, xmin, ymax, xmax))
print(f"Full Heatmap shape: {full_heatmap.shape}")
print(f"Full Overlay shape: {full_overlay.shape}")

# Save outputs to outputs/explainability/
output_dir = Path("outputs/explainability")
output_dir.mkdir(parents=True, exist_ok=True)

crop_overlay_path = output_dir / "apple_scab_crop_attention_rollout.png"
full_overlay_path = output_dir / "apple_scab_full_attention_rollout.png"

Image.fromarray(crop_overlay).save(crop_overlay_path)
Image.fromarray(full_overlay).save(full_overlay_path)

print(f"Saved crop overlay to: {crop_overlay_path.resolve()}")
print(f"Saved full overlay to: {full_overlay_path.resolve()}")
print("SUCCESS: Attention Rollout CAM test verified on real image.")

