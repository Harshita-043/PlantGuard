import { describe, expect, it } from "vitest";

import {
  formatClassName,
  isOodFlagged,
  isProvisionalCandidate,
  validCoverage,
  visualizationModes,
} from "./scan-results";

const classification = {
  primary_class: "Tomato___Late_blight",
  confidence: 0.953,
  is_healthy: false,
  crop_type: "Tomato",
  disease_name: "Late_blight",
  top_k_probabilities: { Tomato___Late_blight: 0.953 },
};

const ood = {
  score: 1200,
  threshold: 2474.6,
  is_ood: false,
  method: "class_conditional_mahalanobis",
  status: "ood_unvalidated" as const,
  calibration_status: "in_distribution_percentile_99_only",
};

const measuredLeaf: Parameters<typeof validCoverage>[0] = {
  segmentation: {
    has_lesions: true,
    diseased_pixels: 9992,
    total_leaf_pixels: 10000,
    diseased_ratio: 0.9992,
    disease_bounding_box: null,
    mask_asset: null,
  },
  severity: {
    status: "available",
    method: "diseased_pixels_intersect_leaf_mask_over_valid_leaf_pixels",
    score: 0.9992,
    level: "high",
    affected_percentage: 99.92,
    diseased_leaf_pixels: 9992,
    valid_leaf_pixels: 10000,
    thresholds_validated: false,
    assessment: "provisional",
  },
};

describe("scan result presentation policies", () => {
  it("keeps an OOD-flagged classifier output separate from accepted candidates", () => {
    const leaf: Parameters<typeof isProvisionalCandidate>[0] = {
      classification,
      ood: { ...ood, is_ood: true },
    };

    expect(isOodFlagged(leaf)).toBe(true);
    expect(isProvisionalCandidate(leaf)).toBe(false);
  });

  it("fails closed when the OOD flag conflicts with its score and threshold", () => {
    const leaf: Parameters<typeof isProvisionalCandidate>[0] = {
      classification,
      ood: { ...ood, score: 2511.3 },
    };

    expect(isOodFlagged(leaf)).toBe(true);
    expect(isProvisionalCandidate(leaf)).toBe(false);
  });

  it("labels a classifier result that passed the gate only as provisional", () => {
    const leaf: Parameters<typeof isProvisionalCandidate>[0] = {
      classification,
      ood,
    };

    expect(isOodFlagged(leaf)).toBe(false);
    expect(isProvisionalCandidate(leaf)).toBe(true);
    expect(formatClassName(classification.primary_class)).toBe(
      "Tomato · Late blight",
    );
  });

  it("withholds display coverage when mask counts and severity disagree", () => {
    expect(validCoverage(measuredLeaf)).toBeCloseTo(99.92);
    expect(
      validCoverage({
        ...measuredLeaf,
        severity: { ...measuredLeaf.severity!, affected_percentage: 12 },
      }),
    ).toBeNull();
    expect(
      validCoverage({
        ...measuredLeaf,
        segmentation: { ...measuredLeaf.segmentation!, total_leaf_pixels: 0 },
      }),
    ).toBeNull();
  });

  it("only offers visualizations that the stored result actually references", () => {
    const modes = visualizationModes(
      {
        leaf_crop_asset: null,
        leaf_mask_asset: null,
        segmentation: null,
        lesion_overlay_asset: null,
        explainability: null,
        attention_overlay_asset: null,
      },
      {},
    );
    expect(modes).toEqual([]);
  });
});
