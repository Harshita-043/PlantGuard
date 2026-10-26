# Reliability and OOD status

## What the pipeline reports

PlantGuard keeps four different signals distinct:

- **Input quality:** malformed, oversized, undecodable, non-finite, or contract-invalid inputs fail validation (`backend/app/ml/service.py`). A missing/empty accepted SAM leaf candidate is a typed no-leaf error.
- **Classification confidence:** the selected DINOv2 ViT-B/14 class softmax probability is exposed in `ClassificationResult.confidence`. A value below `PLANTGUARD_MIN_CLASSIFICATION_CONFIDENCE` (default `0.40`) adds `LOW_CLASSIFICATION_CONFIDENCE`.
- **Prediction uncertainty:** normalized Shannon entropy of the 38-class probability vector is exposed in `prediction_uncertainty.score`; threshold `PLANTGUARD_UNCERTAINTY_THRESHOLD` (default `0.65`) adds a high-uncertainty warning. The result also retains the selected class confidence and labels calibration `incomplete`.
- **OOD:** there is no validated OOD detector in this repository. The pipeline leaves its `ood` result unset. Entropy and maximum softmax probability are provisional warning signals reported through `PredictionUncertainty`; the older standalone `OODDetector` helper still returns an `OODResult.is_ood` threshold flag for compatibility, but it is not used as the service's OOD result. Energy scoring in `backend/app/ml/ood.py` is also uncalibrated and is not used by the pipeline.

The defaults preserve the earlier helper's thresholds. They were not selected from a held-out calibration set, and are configurable through the environment settings shown in `backend/.env.example`. Changing a threshold changes a warning boundary, not model weights or validated performance. Plant/disease labels outside the model's 38-class label map cannot be reliably named as unsupported; diffuse or low-confidence model outputs can warn that such an input may be unsupported.

## Validation status

There is no calibration dataset, calibration procedure, reliability diagram, OOD benchmark, or held-out threshold selection in this repository. Calibration is **incomplete**. No sensitivity, specificity, AUROC, false acceptance rate, or calibrated confidence claim is made. Current CPU tests check the math, validation boundaries, configurable threshold behavior, and output contract only. They do not establish predictive reliability.

Before production use, define supported and unsupported plant/disease cohorts, collect a held-out calibration set representative of real image capture conditions, pre-register threshold selection criteria, evaluate confidence calibration and OOD detection separately, and report subgroup results. Review the warnings with a plant pathology domain expert.
