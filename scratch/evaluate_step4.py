import os
import sys
import time
import json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

import torch
import torch.nn.functional as F
import onnxruntime as ort

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml.architectures.dinov2 import build_dino_disease_classifier, build_dino_leaf_filter

# Class names
classes_file = Path("artifacts/dino_disease/classes.json")
with open(classes_file, "r") as f:
    class_names = json.load(f)

# Preprocessing for 224x224 (DINOv2)
def preprocess_dinov2(image_path, size=224):
    img = Image.open(image_path).convert("RGB")
    # Resize keeping aspect ratio or center crop
    img = img.resize((size, size), Image.Resampling.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    norm = (arr - mean) / std
    chw = np.transpose(norm, (2, 0, 1))
    return np.expand_dims(chw, axis=0).astype(np.float32)

# Preprocessing for 512x512 (SegFormer)
def preprocess_segformer(image_path, size=512):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((size, size), Image.Resampling.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    norm = (arr - mean) / std
    chw = np.transpose(norm, (2, 0, 1))
    return np.expand_dims(chw, axis=0).astype(np.float32)

print("=" * 80)
print("STEP 4A: DISEASE CLASSIFIER COMPARISON")
print("=" * 80)

dc_models = {
    "PyTorch FP32": ("artifacts/dino_disease/dino_disease_classifier.pt", "pytorch"),
    "ONNX FP32": ("artifacts/optimized/dino_disease/onnx/dino_disease_fp32_224.onnx", "onnx"),
    "ONNX Dynamic INT8": ("artifacts/optimized/dino_disease/onnx_int8/dino_disease_dynamic_int8.onnx", "onnx"),
    "ONNX Selective INT8": ("artifacts/optimized/dino_disease/onnx_selective_int8/dino_disease_mlp_int8.onnx", "onnx"),
}

# Load PyTorch model
pt_model = build_dino_disease_classifier()
pt_ckpt = torch.load(dc_models["PyTorch FP32"][0], map_location="cpu")
pt_model.load_state_dict(pt_ckpt.get("state_dict", pt_ckpt), strict=True)
pt_model.eval()

# Load ONNX sessions
onnx_sessions = {}
for name, (path, mtype) in dc_models.items():
    if mtype == "onnx":
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 4
        onnx_sessions[name] = ort.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])

test_images = [
    ("apple-scab-disease-stockcake.jpg", "Apple___Apple_scab"),
    ("test_app.jpg", "Unknown / Leaf"),
    ("plant.jpg", "Unknown / Leaf"),
    ("test.jpg", "Unknown / Leaf"),
]

# Run predictions
results = {name: {"predictions": [], "latencies": [], "size_mb": os.path.getsize(path)/(1024*1024)} for name, (path, _) in dc_models.items()}

for img_path, true_label in test_images:
    if not os.path.exists(img_path):
        continue
    inp = preprocess_dinov2(img_path)
    print(f"\n--- Evaluating image: {img_path} (Expected: {true_label}) ---")
    
    # 1. PyTorch FP32
    with torch.no_grad():
        t_inp = torch.from_numpy(inp)
        logits = pt_model(t_inp)
        probs = F.softmax(logits, dim=-1).numpy()[0]
        top1_idx = int(np.argmax(probs))
        results["PyTorch FP32"]["predictions"].append((img_path, top1_idx, class_names[top1_idx], float(probs[top1_idx]), probs))
        print(f"PyTorch FP32        : {class_names[top1_idx]:<35} (p={probs[top1_idx]:.4f})")

    # ONNX variants
    for name, sess in onnx_sessions.items():
        out = sess.run(None, {sess.get_inputs()[0].name: inp})
        logits_onnx = out[0]
        # softmax
        exp_l = np.exp(logits_onnx - np.max(logits_onnx, axis=-1, keepdims=True))
        probs_onnx = (exp_l / np.sum(exp_l, axis=-1, keepdims=True))[0]
        top1_idx = int(np.argmax(probs_onnx))
        results[name]["predictions"].append((img_path, top1_idx, class_names[top1_idx], float(probs_onnx[top1_idx]), probs_onnx))
        print(f"{name:<20}: {class_names[top1_idx]:<35} (p={probs_onnx[top1_idx]:.4f})")

# Measure Latencies (20 runs after 5 warmups)
dummy_inp = np.random.randn(1, 3, 224, 224).astype(np.float32)
for name, (path, mtype) in dc_models.items():
    times = []
    if mtype == "pytorch":
        t_inp = torch.from_numpy(dummy_inp)
        for _ in range(5):
            with torch.no_grad():
                _ = pt_model(t_inp)
        for _ in range(20):
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = pt_model(t_inp)
            times.append(time.perf_counter() - t0)
    else:
        sess = onnx_sessions[name]
        for _ in range(5):
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_inp})
        for _ in range(20):
            t0 = time.perf_counter()
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_inp})
            times.append(time.perf_counter() - t0)
    median_lat = float(np.median(times) * 1000)
    results[name]["median_lat_ms"] = median_lat
    print(f"Latency {name:<20}: {median_lat:.2f} ms | Size: {results[name]['size_mb']:.1f} MB")

# Parity stats against PyTorch FP32
fp32_probs = [p[4] for p in results["PyTorch FP32"]["predictions"]]
fp32_preds = [p[1] for p in results["PyTorch FP32"]["predictions"]]

print("\n--- Parity vs PyTorch FP32 ---")
for name in dc_models:
    if name == "PyTorch FP32":
        continue
    preds = [p[1] for p in results[name]["predictions"]]
    probs = [p[4] for p in results[name]["predictions"]]
    agree = np.mean([p == f for p, f in zip(preds, fp32_preds)]) * 100
    prob_drift = np.mean([np.max(np.abs(p - f)) for p, f in zip(probs, fp32_probs)])
    mean_abs_err = np.mean([np.mean(np.abs(p - f)) for p, f in zip(probs, fp32_probs)])
    print(f"{name:<20}: Agreement={agree:.1f}%, Max Prob Drift={prob_drift:.4f}, Mean Abs Err={mean_abs_err:.4f}")

print("\n" + "=" * 80)
print("STEP 4B: LEAF FILTER COMPARISON")
print("=" * 80)

lf_models = {
    "PyTorch v1": ("artifacts/dino_leaf_filter/dino_leaf_filter.pt", "pytorch"),
    "PyTorch v2": ("artifacts/dino_leaf_filter/dino_leaf_filter_v2.pt", "pytorch"),
    "ONNX FP32": ("artifacts/optimized/dino_leaf_filter/onnx/dino_leaf_filter_fp32_224.onnx", "onnx"),
    "ONNX Dynamic INT8": ("artifacts/optimized/dino_leaf_filter/onnx_int8/dino_leaf_filter_dynamic_int8.onnx", "onnx"),
}

# Test inputs for leaf filter: real leaves + non-leaf synthetic
lf_test_inputs = [
    ("apple-scab-disease-stockcake.jpg", True),
    ("plant.jpg", True),
    ("test.jpg", True),
    ("random_noise", False),
    ("black_image", False),
    ("white_image", False),
]

lf_results = {name: {"predictions": [], "size_mb": os.path.getsize(path)/(1024*1024)} for name, (path, _) in lf_models.items()}

# Load PyTorch leaf filter v1 & v2
pt_lf_v1 = build_dino_leaf_filter()
pt_lf_v1.load_state_dict(torch.load(lf_models["PyTorch v1"][0], map_location="cpu").get("state_dict", torch.load(lf_models["PyTorch v1"][0], map_location="cpu")), strict=True)
pt_lf_v1.eval()

pt_lf_v2 = build_dino_leaf_filter()
pt_lf_v2.load_state_dict(torch.load(lf_models["PyTorch v2"][0], map_location="cpu").get("state_dict", torch.load(lf_models["PyTorch v2"][0], map_location="cpu")), strict=True)
pt_lf_v2.eval()

lf_onnx_sessions = {}
for name in ["ONNX FP32", "ONNX Dynamic INT8"]:
    path = lf_models[name][0]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    lf_onnx_sessions[name] = ort.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])

for item, is_leaf in lf_test_inputs:
    if item == "random_noise":
        inp = np.random.randn(1, 3, 224, 224).astype(np.float32)
    elif item == "black_image":
        inp = np.zeros((1, 3, 224, 224), dtype=np.float32)
    elif item == "white_image":
        inp = np.ones((1, 3, 224, 224), dtype=np.float32)
    else:
        if not os.path.exists(item):
            continue
        inp = preprocess_dinov2(item)

    print(f"\n--- Leaf Filter Input: {item} (Expected leaf: {is_leaf}) ---")
    with torch.no_grad():
        t_inp = torch.from_numpy(inp)
        p1 = float(torch.sigmoid(pt_lf_v1(t_inp)).numpy()[0][0])
        p2 = float(torch.sigmoid(pt_lf_v2(t_inp)).numpy()[0][0])
    print(f"PyTorch v1          : leaf_prob={p1:.4f} (Decision: {'LEAF' if p1 >= 0.5 else 'NON-LEAF'})")
    print(f"PyTorch v2          : leaf_prob={p2:.4f} (Decision: {'LEAF' if p2 >= 0.5 else 'NON-LEAF'})")
    
    for name, sess in lf_onnx_sessions.items():
        out = sess.run(None, {sess.get_inputs()[0].name: inp})
        logit = out[0].squeeze()
        p_onnx = float(1.0 / (1.0 + np.exp(-logit)))
        print(f"{name:<20}: leaf_prob={p_onnx:.4f} (Decision: {'LEAF' if p_onnx >= 0.5 else 'NON-LEAF'})")

# Measure Leaf Filter Latencies
for name, (path, mtype) in lf_models.items():
    times = []
    if name == "PyTorch v1":
        m = pt_lf_v1
    elif name == "PyTorch v2":
        m = pt_lf_v2
    else:
        m = None

    if m is not None:
        t_inp = torch.from_numpy(dummy_inp)
        for _ in range(5):
            with torch.no_grad():
                _ = m(t_inp)
        for _ in range(20):
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = m(t_inp)
            times.append(time.perf_counter() - t0)
    else:
        sess = lf_onnx_sessions[name]
        for _ in range(5):
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_inp})
        for _ in range(20):
            t0 = time.perf_counter()
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_inp})
            times.append(time.perf_counter() - t0)
    med = float(np.median(times) * 1000)
    print(f"Latency {name:<20}: {med:.2f} ms | Size: {lf_results[name]['size_mb']:.1f} MB")

print("\n" + "=" * 80)
print("STEP 4C: SEGFORMER COMPARISON")
print("=" * 80)

seg_models = {
    "PyTorch reference": "outputs/segformer_plantseg/best_model",
    "ONNX FP32": "artifacts/optimized/segformer/onnx/segformer_fp32_512.onnx",
    "ONNX Dynamic INT8": "artifacts/optimized/segformer/onnx_int8/segformer_dynamic_int8.onnx",
}

from transformers import SegformerForSemanticSegmentation
seg_pt = SegformerForSemanticSegmentation.from_pretrained(seg_models["PyTorch reference"])
seg_pt.eval()

seg_onnx_sessions = {}
for name in ["ONNX FP32", "ONNX Dynamic INT8"]:
    path = seg_models[name]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 4
    seg_onnx_sessions[name] = ort.InferenceSession(path, sess_options=opts, providers=["CPUExecutionProvider"])

for img_path, _ in test_images[:2]:
    if not os.path.exists(img_path):
        continue
    inp = preprocess_segformer(img_path)
    print(f"\n--- SegFormer on: {img_path} ---")
    
    # PyTorch
    with torch.no_grad():
        out_pt = seg_pt(torch.from_numpy(inp)).logits
        mask_pt = torch.argmax(out_pt, dim=1).numpy()[0]
        pct_pt = float(np.mean(mask_pt == 1) * 100)
    print(f"PyTorch reference   : lesion_pct={pct_pt:.2f}%")

    masks = {"PyTorch reference": mask_pt}
    # ONNX FP32 & INT8
    for name in ["ONNX FP32", "ONNX Dynamic INT8"]:
        sess = seg_onnx_sessions[name]
        out = sess.run(None, {sess.get_inputs()[0].name: inp})[0]
        mask = np.argmax(out, axis=1)[0]
        pct = float(np.mean(mask == 1) * 100)
        masks[name] = mask
        print(f"{name:<20}: lesion_pct={pct:.2f}% (error vs PT: {abs(pct - pct_pt):.3f} points)")

    # Compute IoU between INT8 and FP32
    fp32_m = masks["ONNX FP32"] == 1
    int8_m = masks["ONNX Dynamic INT8"] == 1
    intersection = np.logical_and(fp32_m, int8_m).sum()
    union = np.logical_or(fp32_m, int8_m).sum()
    iou = 1.0 if union == 0 else float(intersection / union)
    print(f"Mask IoU (ONNX INT8 vs ONNX FP32): {iou:.4f}")

# Measure SegFormer Latencies
dummy_512 = np.random.randn(1, 3, 512, 512).astype(np.float32)
for name in seg_models:
    times = []
    if name == "PyTorch reference":
        t_inp = torch.from_numpy(dummy_512)
        for _ in range(3):
            with torch.no_grad():
                _ = seg_pt(t_inp)
        for _ in range(10):
            t0 = time.perf_counter()
            with torch.no_grad():
                _ = seg_pt(t_inp)
            times.append(time.perf_counter() - t0)
        size_mb = os.path.getsize("outputs/segformer_plantseg/best_model/model.safetensors") / (1024*1024)
    else:
        sess = seg_onnx_sessions[name]
        for _ in range(3):
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_512})
        for _ in range(10):
            t0 = time.perf_counter()
            _ = sess.run(None, {sess.get_inputs()[0].name: dummy_512})
            times.append(time.perf_counter() - t0)
        size_mb = os.path.getsize(seg_models[name]) / (1024*1024)
    med = float(np.median(times) * 1000)
    print(f"Latency {name:<20}: {med:.2f} ms | Size: {size_mb:.1f} MB")

