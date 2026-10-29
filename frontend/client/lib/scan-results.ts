import type { MaskAsset, SingleLeafAnalysis } from "@shared/api";

export function isOodRejected(leaf: Pick<SingleLeafAnalysis, "ood">) {
  const ood = leaf.ood;
  return Boolean(
    ood &&
    (ood.is_ood ||
      (Number.isFinite(ood.score) &&
        Number.isFinite(ood.threshold) &&
        ood.score > ood.threshold)),
  );
}

export function isProvisionalCandidate(
  leaf: Pick<SingleLeafAnalysis, "classification" | "ood">,
) {
  return Boolean(
    leaf.classification &&
    leaf.ood &&
    !isOodRejected(leaf) &&
    leaf.ood.status !== "ood_unavailable",
  );
}

export function formatClassName(value: string) {
  return value.replace(/___/g, " · ").replace(/_/g, " ");
}

export function validCoverage(
  leaf: Pick<SingleLeafAnalysis, "segmentation" | "severity">,
): number | null {
  const segmentation = leaf.segmentation;
  const severity = leaf.severity;
  if (
    !segmentation ||
    !severity ||
    severity.status !== "available" ||
    !Number.isFinite(segmentation.diseased_ratio) ||
    segmentation.diseased_ratio < 0 ||
    segmentation.diseased_ratio > 1 ||
    segmentation.total_leaf_pixels <= 0 ||
    segmentation.diseased_pixels < 0 ||
    segmentation.diseased_pixels > segmentation.total_leaf_pixels ||
    severity.valid_leaf_pixels !== segmentation.total_leaf_pixels ||
    severity.diseased_leaf_pixels !== segmentation.diseased_pixels ||
    severity.affected_percentage === null ||
    !Number.isFinite(severity.affected_percentage)
  ) {
    return null;
  }
  const countRatio =
    segmentation.diseased_pixels / segmentation.total_leaf_pixels;
  const percentFromRatio = segmentation.diseased_ratio * 100;
  if (
    Math.abs(countRatio - segmentation.diseased_ratio) > 0.001 ||
    Math.abs(severity.affected_percentage - percentFromRatio) > 0.02
  ) {
    return null;
  }
  return percentFromRatio;
}

export function visualizationModes(
  leaf: Pick<
    SingleLeafAnalysis,
    | "leaf_crop_asset"
    | "leaf_mask_asset"
    | "segmentation"
    | "lesion_overlay_asset"
    | "explainability"
    | "attention_overlay_asset"
  >,
  sources: Record<string, string>,
) {
  const available: Array<[string, string, MaskAsset | null | undefined]> = [
    ["crop", "Leaf crop", leaf.leaf_crop_asset],
    ["leaf-mask", "Leaf mask", leaf.leaf_mask_asset],
    ["lesion-mask", "Lesion mask", leaf.segmentation?.mask_asset],
    ["lesion-overlay", "Lesion overlay", leaf.lesion_overlay_asset],
    [
      "attention-rollout",
      "Attention rollout",
      leaf.explainability?.heatmap_asset,
    ],
    ["attention-overlay", "Attention overlay", leaf.attention_overlay_asset],
  ];
  return available.flatMap(([id, label, asset]) =>
    asset ? [{ id, label, source: sources[asset.storage_key] ?? null }] : [],
  );
}
