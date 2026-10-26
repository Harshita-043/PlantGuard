# Mask-based severity method

## Formula and masks

For one selected leaf crop, the pipeline uses the verified SegFormer mapping `0=background`, `1=diseased_region` and the corresponding SAM 2.1 candidate leaf mask. The saved SegFormer preprocessing metadata determines input normalization and resolution; the adapter upsamples logits to the crop's original height and width with bilinear interpolation (`align_corners=False`) and applies `argmax`. The leaf mask remains binary and is resized, only if necessary, with nearest-neighbor interpolation.

The valid region is exactly the nonzero pixels in the aligned selected-leaf mask. The numerator is the count of pixels where the SegFormer class is `1` **and** the selected-leaf mask is nonzero. Any predicted lesion pixels outside the selected leaf are excluded:

```text
severity_percentage = diseased_leaf_pixels / valid_leaf_pixels * 100
```

The output includes `diseased_leaf_pixels`, `valid_leaf_pixels`, `affected_percentage`, the method identifier, and `score` (the fraction from 0 to 1). Lesion component counts are computed from the same intersected binary mask. The method is a pixel coverage estimate, not an expert severity rating.

If the leaf mask is absent, empty, non-finite, or misaligned, or the disease mask is empty/invalid, severity has `status=unavailable` and no numeric estimate. If the checkpoint label mapping fails the adapter's configured mapping check, segmentation fails closed and severity is not fabricated. Zero diseased pixels within a valid leaf is a valid 0% result.

The legacy `LeafResult` adapter carries `severity_status` and nullable score, level, and percentage fields so unavailable estimates do not become synthetic zero values. The model-native result remains the source of the pixel counts and method identifier.

## Categories and configuration

The default provisional categories in `backend/app/ml/severity.py` are:

| Affected leaf pixels | Level |
| --- | --- |
| exactly 0% | healthy |
| greater than 0% through 15% | low |
| greater than 15% through 35% | medium |
| greater than 35% | high |

Set `PLANTGUARD_SEVERITY_LOW_THRESHOLD_PCT` and `PLANTGUARD_SEVERITY_MEDIUM_THRESHOLD_PCT` before the backend starts. Valid configuration requires `0 <= low < medium <= 100`. Thresholds are not stored in or applied to the model checkpoint. The defaults came from the pre-existing estimator and have **not** been validated by agronomic outcome data; every returned available estimate marks `thresholds_validated=false` and the pipeline warns accordingly.

## Validation still required

CPU tests verify denominator, clipping, empty masks, mask alignment, full/empty masks, and every default boundary. They do not assess SegFormer mask quality, SAM boundary quality, image-registration error, or whether pixel coverage predicts expert-rated disease severity. Those require actual model artifacts and an independently reviewed, annotated dataset.
