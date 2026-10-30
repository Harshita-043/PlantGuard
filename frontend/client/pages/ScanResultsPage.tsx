import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Leaf,
  Loader,
  ShieldAlert,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import {
  AnalysisAssetLink,
  AnalysisLifecycleResponse,
  ApiError,
  analysisApi,
} from "@/lib/api";
import LeafOverlay from "@/components/scan/LeafOverlay";
import {
  formatClassName,
  isOodFlagged,
  isProvisionalCandidate,
  validCoverage,
  visualizationModes,
} from "@/lib/scan-results";

const summarizedWarningCodes = new Set([
  "RELIABILITY_UNCALIBRATED",
  "SEVERITY_THRESHOLDS_UNVALIDATED",
  "OOD_FLAGGED_UNVALIDATED",
  "OOD_ABSTENTION_UNVALIDATED",
  "LOW_CLASSIFICATION_CONFIDENCE",
  "HIGH_PREDICTION_UNCERTAINTY",
]);

export default function ScanResultsPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { accessToken, logout } = useAuth();
  const [analysis, setAnalysis] = useState<AnalysisLifecycleResponse | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assetError, setAssetError] = useState<string | null>(null);
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);
  const [assetLinks, setAssetLinks] = useState<AnalysisAssetLink[]>([]);
  const [assetSources, setAssetSources] = useState<Record<string, string>>({});
  const [failedAssetKeys, setFailedAssetKeys] = useState<Set<string>>(
    new Set(),
  );
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadAnalysis() {
      if (!scanId || !accessToken) {
        setError("A valid analysis ID and sign-in are required.");
        setIsLoading(false);
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const record = await analysisApi.getAnalysis(scanId, accessToken);
        if (active) setAnalysis(record);
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        if (active)
          setError(
            caught instanceof Error
              ? caught.message
              : "Could not load this analysis.",
          );
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void loadAnalysis();
    return () => {
      active = false;
    };
  }, [accessToken, logout, navigate, scanId]);

  useEffect(() => {
    let active = true;
    const objectUrls: string[] = [];
    async function loadAssets() {
      if (!analysis || !accessToken) return;
      setAssetError(null);
      setIsLoadingAssets(true);
      try {
        const response = await analysisApi.getAnalysisAssets(
          analysis.analysis_id,
          accessToken,
        );
        const resolved = await Promise.all(
          response.assets.map(async (asset) => {
            try {
              if (asset.download_url.startsWith("https://")) {
                return { key: asset.storage_key, source: asset.download_url };
              }
              const blob = await analysisApi.getAssetBlob(
                asset.download_url,
                accessToken,
              );
              const source = URL.createObjectURL(blob);
              objectUrls.push(source);
              return { key: asset.storage_key, source };
            } catch (caught) {
              if (caught instanceof ApiError && caught.status === 401) {
                throw caught;
              }
              return { key: asset.storage_key, source: null };
            }
          }),
        );
        if (active) {
          setAssetLinks(response.assets);
          setAssetSources(
            Object.fromEntries(
              resolved.flatMap(({ key, source }) =>
                source ? [[key, source]] : [],
              ),
            ),
          );
          setFailedAssetKeys(
            new Set(
              resolved.filter(({ source }) => !source).map(({ key }) => key),
            ),
          );
        } else {
          objectUrls.forEach((url) => URL.revokeObjectURL(url));
        }
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        if (active)
          setAssetError(
            caught instanceof Error
              ? caught.message
              : "Analysis images could not be loaded.",
          );
      } finally {
        if (active) setIsLoadingAssets(false);
      }
    }
    void loadAssets();
    return () => {
      active = false;
      objectUrls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [accessToken, analysis, logout, navigate]);

  const deleteCurrentAnalysis = async () => {
    if (!scanId || !accessToken || isDeleting) return;
    if (
      !window.confirm(
        "Delete this analysis and its stored images? This cannot be undone.",
      )
    )
      return;
    setIsDeleting(true);
    setError(null);
    try {
      await analysisApi.deleteAnalysis(scanId, accessToken);
      navigate("/history", { replace: true });
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(
        caught instanceof Error
          ? caught.message
          : "The analysis could not be deleted.",
      );
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="grid min-h-[50vh] place-items-center">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader size={18} className="animate-spin" />
          Loading saved analysis…
        </p>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <section className="mx-auto max-w-xl space-y-4 rounded-2xl border border-border bg-card p-8 text-center">
        <AlertTriangle size={26} className="mx-auto text-destructive" />
        <h2 className="text-xl font-semibold">Could not load this analysis</h2>
        <p className="text-sm text-muted-foreground">
          {error ?? "Analysis not found."}
        </p>
        <Button variant="outline" onClick={() => navigate("/scan")}>
          Back to scan
        </Button>
      </section>
    );
  }

  const result = analysis.result;
  const oodFlaggedLeaves = result?.leaves.filter(isOodFlagged) ?? [];
  const classifierOutputs =
    result?.leaves.filter((leaf) => leaf.classification !== null) ?? [];
  const candidateLeaves = result?.leaves.filter(isProvisionalCandidate) ?? [];
  const unverifiedPredictions =
    result?.leaves.filter(
      (leaf) =>
        leaf.classification &&
        !isProvisionalCandidate(leaf) &&
        !isOodFlagged(leaf),
    ) ?? [];
  const hasOodFlag = oodFlaggedLeaves.length > 0;
  const original = assetLinks.find((asset) => asset.kind === "original");
  const originalSource = original
    ? assetSources[original.storage_key]
    : undefined;
  const uniqueWarnings = new Map(
    [
      ...(result?.warnings ?? []),
      ...(result?.leaves.flatMap((leaf) => leaf.warnings) ?? []),
    ]
      .filter((warning) => !summarizedWarningCodes.has(warning.code))
      .map((warning) => [`${warning.code}:${warning.message}`, warning]),
  );

  return (
    <main
      className="mx-auto max-w-7xl space-y-7 px-4 py-6 sm:px-6 lg:py-10"
      aria-labelledby="analysis-title"
    >
      <header className="flex flex-col gap-5 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-3">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 w-fit"
            onClick={() => navigate("/history")}
          >
            <ArrowLeft size={16} className="mr-2" />
            Scan history
          </Button>
          <div className="flex items-center gap-3">
            <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary/10 text-primary">
              <Leaf size={22} />
            </span>
            <div className="min-w-0">
              <h1
                id="analysis-title"
                className="text-2xl font-bold tracking-tight sm:text-3xl"
              >
                Scan results
              </h1>
              <p className="mt-1 break-all text-xs text-muted-foreground">
                {analysis.analysis_id}
              </p>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            {new Date(analysis.created_at).toLocaleString()} ·{" "}
            {Math.ceil(analysis.image_size_bytes / 1024)} KB image
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-border px-3 py-1.5 text-sm font-medium capitalize">
            {analysis.status}
          </span>
          <Button variant="outline" onClick={() => navigate("/scan")}>
            Analyze another image
          </Button>
        </div>
      </header>

      {error && (
        <p
          className="rounded-xl border border-destructive/40 p-4 text-sm"
          role="alert"
        >
          {error}
        </p>
      )}
      {assetError && (
        <p
          className="rounded-xl border border-border p-4 text-sm text-muted-foreground"
          role="status"
        >
          Saved images could not be loaded: {assetError}
        </p>
      )}
      {isLoadingAssets && (
        <p className="text-sm text-muted-foreground" role="status">
          Loading saved image visualizations…
        </p>
      )}

      {analysis.status === "failed" && (
        <section
          className="rounded-2xl border border-destructive/40 bg-destructive/5 p-5"
          role="alert"
          aria-labelledby="failed-title"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle
              size={20}
              className="mt-0.5 shrink-0 text-destructive"
            />
            <div>
              <h2 id="failed-title" className="font-semibold">
                Analysis could not be completed
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                No diagnosis or severity result was saved for this scan.
              </p>
            </div>
          </div>
        </section>
      )}
      {analysis.status === "pending" && (
        <section
          className="flex items-start gap-3 rounded-2xl border border-border bg-card p-5"
          role="status"
        >
          <Clock3 size={20} className="mt-0.5 shrink-0 text-muted-foreground" />
          <div>
            <h2 className="font-semibold">Analysis is still processing</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              No inference result is available yet. Refresh this page to check
              again.
            </p>
          </div>
        </section>
      )}
      {analysis.failure && (
        <details className="rounded-xl border border-border bg-card px-4 py-3 text-sm">
          <summary className="cursor-pointer font-medium">
            Failure diagnostics
          </summary>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Stage</dt>
              <dd>{analysis.failure.stage}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Code</dt>
              <dd>{analysis.failure.code}</dd>
            </div>
            <div className="sm:col-span-3">
              <dt className="text-muted-foreground">Message</dt>
              <dd>{analysis.failure.message}</dd>
            </div>
          </dl>
        </details>
      )}

      {result?.status === "partial" && (
        <section
          className="flex items-start gap-3 rounded-2xl border border-amber-500/40 bg-amber-500/5 p-5"
          role="status"
          aria-label="Partial analysis"
        >
          <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-600" />
          <div>
            <h2 className="font-semibold">Partial analysis</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Some stages did not complete. Only available results are shown;
              segmentation or severity may be unavailable for some leaves.
            </p>
          </div>
        </section>
      )}

      {result && (
        <>
          <section
            className={`grid overflow-hidden rounded-2xl border bg-card lg:grid-cols-[minmax(0,1.15fr)_minmax(18rem,0.85fr)] ${
              hasOodFlag ? "border-amber-500/40" : "border-border"
            }`}
            aria-labelledby="diagnosis-title"
          >
            <div className="space-y-5 p-5 sm:p-7">
              <div className="flex items-start gap-3">
                <span
                  className={`grid size-10 shrink-0 place-items-center rounded-xl ${
                    hasOodFlag
                      ? "bg-amber-500/10 text-amber-700 dark:text-amber-300"
                      : "bg-primary/10 text-primary"
                  }`}
                >
                  {hasOodFlag ? (
                    <ShieldAlert size={20} />
                  ) : (
                    <CheckCircle2 size={20} />
                  )}
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    {hasOodFlag ? "Review required" : "Model assessment"}
                  </p>
                  <h2
                    id="diagnosis-title"
                    className="mt-1 text-xl font-bold sm:text-2xl"
                  >
                    {hasOodFlag
                      ? "Potential out-of-distribution input"
                      : candidateLeaves.length > 0
                        ? "Provisional classification candidate"
                        : "No diagnosis available"}
                  </h2>
                </div>
              </div>
              {hasOodFlag ? (
                <div className="space-y-3" role="status">
                  <p className="font-medium">
                    OOD threshold exceeded for {oodFlaggedLeaves.length}{" "}
                    {oodFlaggedLeaves.length === 1 ? "leaf" : "leaves"}.
                  </p>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Classifier outputs are retained and shown below as
                    unverified candidates. The OOD threshold is provisional and
                    has not been independently validated; exceeding it does not
                    confirm that the input is out of distribution.
                  </p>
                  <p className="text-sm leading-relaxed">
                    Review the predicted class together with the OOD flag. Do
                    not treat either model output as a confirmed diagnosis.
                  </p>
                </div>
              ) : candidateLeaves.length > 0 ? (
                <div className="space-y-3">
                  {result.plant_summary.primary_diagnosis && (
                    <p className="text-lg font-semibold">
                      {formatClassName(result.plant_summary.primary_diagnosis)}
                    </p>
                  )}
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    {candidateLeaves.length} candidate{" "}
                    {candidateLeaves.length === 1
                      ? "classification"
                      : "classifications"}{" "}
                    passed the configured OOD threshold. The calibration is
                    incomplete; these labels are not independently validated
                    diagnoses.
                  </p>
                </div>
              ) : (
                <p className="text-sm leading-relaxed text-muted-foreground">
                  No supported classification is available for this scan. This
                  does not mean the plant is healthy.
                </p>
              )}
              {candidateLeaves.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {candidateLeaves.length} leaf label
                  {candidateLeaves.length === 1 ? "" : "s"} available as
                  provisional model candidates.
                </p>
              )}
            </div>
            <figure className="flex min-h-56 items-center justify-center border-t border-border bg-muted/30 p-4 lg:border-l lg:border-t-0">
              {originalSource &&
              original &&
              !failedAssetKeys.has(original.storage_key) ? (
                <img
                  src={originalSource}
                  alt="Original uploaded plant image"
                  className="max-h-80 w-full rounded-xl object-contain"
                  onError={() =>
                    setFailedAssetKeys((current) =>
                      new Set(current).add(original.storage_key),
                    )
                  }
                />
              ) : (
                <div
                  className="max-w-xs text-center text-sm text-muted-foreground"
                  role="status"
                >
                  {isLoadingAssets
                    ? "Loading the uploaded image…"
                    : "Original image unavailable."}
                </div>
              )}
              <figcaption className="sr-only">
                Original image submitted for analysis
              </figcaption>
            </figure>
          </section>

          <section aria-labelledby="metrics-title" className="space-y-3">
            <div>
              <h2 id="metrics-title" className="text-lg font-bold">
                Scan overview
              </h2>
              <p className="text-sm text-muted-foreground">
                Metrics describe model output, not validated agronomic
                measurements.
              </p>
            </div>
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">
                  Leaf candidates
                </dt>
                <dd className="mt-1 text-2xl font-bold">
                  {result.plant_summary.total_leaves_detected}
                </dd>
              </div>
              <div className="rounded-xl border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">
                  Classifier outputs
                </dt>
                <dd className="mt-1 text-2xl font-bold">
                  {classifierOutputs.length}
                </dd>
              </div>
              <div className="rounded-xl border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">
                  Classification confidence
                </dt>
                <dd className="mt-1 text-2xl font-bold">
                  {classifierOutputs.length
                    ? `${((classifierOutputs.reduce((sum, leaf) => sum + (leaf.classification?.confidence ?? 0), 0) / classifierOutputs.length) * 100).toFixed(1)}%`
                    : "Unavailable"}
                </dd>
                {classifierOutputs.length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Mean raw score; not calibrated
                  </p>
                )}
              </div>
              <div className="rounded-xl border border-border bg-card p-4">
                <dt className="text-sm text-muted-foreground">
                  Processing time
                </dt>
                <dd className="mt-1 text-2xl font-bold">
                  {(result.processing_time_ms / 1000).toFixed(1)} s
                </dd>
                <p className="mt-1 text-xs text-muted-foreground">
                  Runtime: {result.hardware_device}
                </p>
              </div>
            </dl>
          </section>

          <section aria-labelledby="leaves-title" className="space-y-4">
            <div>
              <h2 id="leaves-title" className="text-lg font-bold">
                Leaf analysis
              </h2>
              <p className="text-sm text-muted-foreground">
                Each card keeps classification, mask coverage, and visual
                evidence together.
              </p>
            </div>
            {result.leaves.length === 0 ? (
              <p className="rounded-xl border border-dashed border-border p-5 text-sm text-muted-foreground">
                No leaf candidates were returned for this scan.
              </p>
            ) : (
              <div className="grid gap-4 xl:grid-cols-2">
                {result.leaves.map((leaf) => {
                  const oodFlagged = isOodFlagged(leaf);
                  const coverage = validCoverage(leaf);
                  const modes = visualizationModes(leaf, assetSources);
                  const uncertainty = leaf.prediction_uncertainty;
                  return (
                    <article
                      key={leaf.leaf_id}
                      className="min-w-0 space-y-4 rounded-2xl border border-border bg-card p-4 sm:p-5"
                    >
                      <header className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h3 className="text-base font-bold">
                            Leaf {leaf.leaf_id + 1}
                          </h3>
                          <p className="mt-1 text-xs text-muted-foreground">
                            Detection score{" "}
                            {(leaf.leaf_filter_confidence * 100).toFixed(1)}%
                          </p>
                        </div>
                        <span
                          className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                            oodFlagged
                              ? "border-amber-500/40 bg-amber-500/10 text-amber-900 dark:text-amber-200"
                              : leaf.classification
                                ? "border-primary/30 bg-primary/5 text-foreground"
                                : "border-border text-muted-foreground"
                          }`}
                        >
                          {oodFlagged
                            ? leaf.classification
                              ? "OOD flagged · unverified candidate"
                              : "OOD flagged · no class output"
                            : isProvisionalCandidate(leaf)
                              ? "Provisional candidate"
                              : leaf.classification
                                ? "Unverified output"
                                : "Unclassified"}
                        </span>
                      </header>

                      {oodFlagged && !leaf.classification ? (
                        <div
                          className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-3"
                          role="status"
                        >
                          <p className="font-semibold">Potential OOD input</p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            This leaf exceeded the provisional OOD threshold; no
                            classifier output is available.
                          </p>
                        </div>
                      ) : leaf.classification ? (
                        <div className="rounded-xl bg-muted/50 p-3">
                          <p className="text-xs text-muted-foreground">
                            {oodFlagged
                              ? "Unverified model candidate · OOD flagged"
                              : isProvisionalCandidate(leaf)
                                ? "Provisional model candidate"
                                : "Unverified classifier output"}
                          </p>
                          <p className="mt-1 font-semibold">
                            {formatClassName(leaf.classification.primary_class)}
                          </p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            Raw confidence{" "}
                            {(leaf.classification.confidence * 100).toFixed(1)}%
                            · not calibrated
                          </p>
                          {oodFlagged && (
                            <p className="mt-2 text-sm text-amber-800 dark:text-amber-200">
                              OOD threshold exceeded; review this candidate
                              cautiously.
                            </p>
                          )}
                        </div>
                      ) : (
                        <p className="rounded-xl bg-muted/50 p-3 text-sm text-muted-foreground">
                          No classification is available. The plant is not
                          therefore considered healthy.
                        </p>
                      )}

                      <dl className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-lg border border-border p-3">
                          <dt className="text-xs text-muted-foreground">
                            Lesion-mask coverage
                          </dt>
                          <dd className="mt-1 font-semibold">
                            {coverage === null
                              ? "Unavailable"
                              : `${coverage.toFixed(2)}% · provisional`}
                          </dd>
                          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                            {coverage === null
                              ? "Segmentation counts or mask alignment did not satisfy the display contract."
                              : oodFlagged
                                ? "The OOD threshold was exceeded; segmentation and severity for this candidate are unvalidated."
                                : "Pixel ratio from the model mask; severity thresholds are not agronomically validated."}
                          </p>
                        </div>
                        <div className="rounded-lg border border-border p-3">
                          <dt className="text-xs text-muted-foreground">
                            OOD flag
                          </dt>
                          <dd className="mt-1 font-semibold">
                            {leaf.ood
                              ? oodFlagged
                                ? "Threshold exceeded"
                                : "Threshold not exceeded"
                              : "Unavailable"}
                          </dd>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {leaf.ood?.calibration_status.replace(/_/g, " ") ??
                              "No OOD result returned"}
                            ; performance not validated.
                          </p>
                        </div>
                      </dl>

                      <div className="border-t border-border pt-4">
                        <h4 className="mb-3 text-sm font-semibold">
                          Visual evidence
                        </h4>
                        <LeafOverlay
                          leafId={leaf.leaf_id}
                          modes={modes}
                          onImageError={(source) => {
                            const failed = assetLinks.find(
                              (asset) =>
                                assetSources[asset.storage_key] === source,
                            );
                            if (failed) {
                              setFailedAssetKeys((current) =>
                                new Set(current).add(failed.storage_key),
                              );
                            }
                          }}
                        />
                      </div>

                      <details className="rounded-lg border border-border px-3 py-2 text-sm">
                        <summary className="cursor-pointer font-medium">
                          Leaf technical diagnostics
                        </summary>
                        <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Classifier confidence
                            </dt>
                            <dd>
                              {leaf.classification
                                ? leaf.classification.confidence.toFixed(4)
                                : "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Entropy (normalized; provisional)
                            </dt>
                            <dd>
                              {uncertainty
                                ? `${uncertainty.score.toFixed(4)} / threshold ${uncertainty.threshold.toFixed(4)}`
                                : "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Mahalanobis distance / threshold
                            </dt>
                            <dd>
                              {leaf.ood?.method ===
                              "class_conditional_mahalanobis"
                                ? `${leaf.ood.score.toFixed(2)} / ${leaf.ood.threshold.toFixed(2)}`
                                : "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              OOD decision
                            </dt>
                            <dd>
                              {leaf.ood
                                ? oodFlagged
                                  ? "Exceeded provisional threshold"
                                  : "Did not exceed provisional threshold"
                                : "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Calibration
                            </dt>
                            <dd>
                              {leaf.ood?.calibration_status.replace(
                                /_/g,
                                " ",
                              ) ?? "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Segmentation
                            </dt>
                            <dd>
                              {leaf.segmentation
                                ? `${leaf.segmentation.diseased_pixels} / ${leaf.segmentation.total_leaf_pixels} mask pixels`
                                : "Unavailable"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Segmentation contract
                            </dt>
                            <dd>
                              {coverage === null
                                ? "Missing or inconsistent output"
                                : "Pixel counts and ratio agree; biological validity is unverified"}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-xs text-muted-foreground">
                              Severity thresholds
                            </dt>
                            <dd>
                              {leaf.severity?.thresholds_validated
                                ? "Validated"
                                : "Not validated"}
                            </dd>
                          </div>
                          {leaf.warnings
                            .filter(
                              (warning) =>
                                !summarizedWarningCodes.has(warning.code),
                            )
                            .map((warning) => (
                              <div
                                key={`${warning.code}:${warning.message}`}
                                className="sm:col-span-2"
                              >
                                <dt className="text-xs text-muted-foreground">
                                  {warning.code.replace(/_/g, " ")}
                                </dt>
                                <dd>{warning.message}</dd>
                              </div>
                            ))}
                          {unverifiedPredictions.map((leaf) => (
                            <div
                              key={`unverified-${leaf.leaf_id}`}
                              className="sm:col-span-2"
                            >
                              <dt className="text-muted-foreground">
                                Classifier output · leaf {leaf.leaf_id + 1}
                              </dt>
                              <dd>
                                {leaf.classification
                                  ? `${formatClassName(leaf.classification.primary_class)} · raw confidence ${leaf.classification.confidence.toFixed(4)}; ${isOodFlagged(leaf) ? "OOD threshold exceeded; unverified candidate." : "no usable OOD acceptance result."}`
                                  : "Unavailable"}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section
            aria-labelledby="recommendations-title"
            className="rounded-2xl border border-border bg-card p-5 sm:p-6"
          >
            <h2 id="recommendations-title" className="text-lg font-bold">
              Next steps
            </h2>
            {hasOodFlag ? (
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                Capture a new close, well-lit image of one leaf and submit it
                for review. Avoid disease-specific treatment based on this scan.
              </p>
            ) : result.plant_summary.recommendations.length > 0 ? (
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm">
                {result.plant_summary.recommendations.map(
                  (recommendation, index) => (
                    <li key={`${index}:${recommendation}`}>{recommendation}</li>
                  ),
                )}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">
                No recommendations were returned for this analysis.
              </p>
            )}
          </section>

          <details className="rounded-2xl border border-border bg-card p-5 sm:p-6">
            <summary className="cursor-pointer text-base font-bold">
              Technical diagnostics
            </summary>
            <p className="mt-2 text-sm text-muted-foreground">
              Confidence and entropy are model signals, not calibrated
              probabilities. Mahalanobis calibration uses an in-distribution
              percentile threshold and has not been independently validated for
              OOD performance.
            </p>
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="text-muted-foreground">Analysis status</dt>
                <dd>{result.status}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Device</dt>
                <dd>{result.hardware_device}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Elapsed time</dt>
                <dd>{result.processing_time_ms} ms</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">
                  Leaves detected / analyzed
                </dt>
                <dd>
                  {result.plant_summary.total_leaves_detected} /{" "}
                  {result.plant_summary.valid_leaves_analyzed}
                </dd>
              </div>
              {result.candidate_counts && (
                <div className="sm:col-span-2">
                  <dt className="text-muted-foreground">
                    Candidates: generated / valid / deduplicated / leaf accepted
                    / disease eligible
                  </dt>
                  <dd>
                    {result.candidate_counts.generated} /{" "}
                    {result.candidate_counts.valid} /{" "}
                    {result.candidate_counts.deduplicated} /{" "}
                    {result.candidate_counts.leaf_filter_accepted} /{" "}
                    {result.candidate_counts.disease_analysis_eligible}
                  </dd>
                </div>
              )}
              {Object.entries(result.model_versions).map(([name, version]) => (
                <div key={name}>
                  <dt className="text-muted-foreground">
                    {name.replace(/_/g, " ")}
                  </dt>
                  <dd>{version}</dd>
                </div>
              ))}
              {Object.entries(result.stage_timings_ms).map(
                ([stage, duration]) => (
                  <div key={stage}>
                    <dt className="text-muted-foreground">
                      {stage.replace(/_/g, " ")}
                    </dt>
                    <dd>{duration} ms</dd>
                  </div>
                ),
              )}
              {Array.from(uniqueWarnings.values()).map((warning) => (
                <div
                  key={`${warning.code}:${warning.message}`}
                  className="sm:col-span-2"
                >
                  <dt className="text-muted-foreground">
                    {warning.code.replace(/_/g, " ")}
                  </dt>
                  <dd>{warning.message}</dd>
                </div>
              ))}
            </dl>
            {result.partial_failures.length > 0 && (
              <div className="mt-4 border-t border-border pt-4">
                <h3 className="font-semibold">Partial failures</h3>
                <ul className="mt-2 space-y-2 text-sm">
                  {result.partial_failures.map((failure, index) => (
                    <li key={`${failure.component}-${index}`}>
                      {failure.component}: {failure.error_type} —{" "}
                      {failure.message}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </details>
        </>
      )}
      {analysis.status === "completed" && !result && (
        <p
          className="rounded-xl border border-destructive/40 p-4 text-sm"
          role="alert"
        >
          The record is marked completed but contains no result. No diagnosis is
          shown.
        </p>
      )}

      <footer className="flex flex-wrap justify-end gap-3 border-t border-border pt-5">
        <Button variant="outline" onClick={() => navigate("/history")}>
          View scan history
        </Button>
        <Button
          variant="destructive"
          onClick={() => void deleteCurrentAnalysis()}
          disabled={isDeleting}
        >
          {isDeleting ? (
            <Loader size={16} className="mr-2 animate-spin" />
          ) : (
            <Trash2 size={16} className="mr-2" />
          )}
          Delete analysis
        </Button>
      </footer>
    </main>
  );
}
