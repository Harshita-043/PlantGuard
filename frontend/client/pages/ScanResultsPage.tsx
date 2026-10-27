import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, Clock3, Leaf, Loader, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { AnalysisAssetLink, AnalysisLifecycleResponse, ApiError, analysisApi } from "@/lib/api";

export default function ScanResultsPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { accessToken, logout } = useAuth();
  const [analysis, setAnalysis] = useState<AnalysisLifecycleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assetError, setAssetError] = useState<string | null>(null);
  const [assetLinks, setAssetLinks] = useState<AnalysisAssetLink[]>([]);
  const [assetSources, setAssetSources] = useState<Record<string, string>>({});
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
        if (active) setError(caught instanceof Error ? caught.message : "Could not load this analysis.");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void loadAnalysis();
    return () => { active = false; };
  }, [accessToken, logout, navigate, scanId]);

  useEffect(() => {
    let active = true;
    const objectUrls: string[] = [];
    async function loadAssets() {
      if (!analysis || !accessToken) return;
      setAssetError(null);
      try {
        const response = await analysisApi.getAnalysisAssets(analysis.analysis_id, accessToken);
        const resolved = await Promise.all(response.assets.map(async (asset) => {
          if (asset.download_url.startsWith("https://")) {
            return [asset.storage_key, asset.download_url] as const;
          }
          const blob = await analysisApi.getAssetBlob(asset.download_url, accessToken);
          const source = URL.createObjectURL(blob);
          objectUrls.push(source);
          return [asset.storage_key, source] as const;
        }));
        if (active) {
          setAssetLinks(response.assets);
          setAssetSources(Object.fromEntries(resolved));
        } else {
          objectUrls.forEach((url) => URL.revokeObjectURL(url));
        }
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        if (active) setAssetError(caught instanceof Error ? caught.message : "Analysis images could not be loaded.");
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
    if (!window.confirm("Delete this analysis and its stored images? This cannot be undone.")) return;
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
      setError(caught instanceof Error ? caught.message : "The analysis could not be deleted.");
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return <div className="grid min-h-[50vh] place-items-center"><p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader size={18} className="animate-spin" />Loading saved analysis…</p></div>;
  }

  if (error || !analysis) {
    return (
      <section className="mx-auto max-w-xl space-y-4 rounded-2xl border border-border bg-card p-8 text-center">
        <AlertTriangle size={26} className="mx-auto text-destructive" />
        <h2 className="text-xl font-semibold">Could not load this analysis</h2>
        <p className="text-sm text-muted-foreground">{error ?? "Analysis not found."}</p>
        <Button variant="outline" onClick={() => navigate("/scan")}>Back to scan</Button>
      </section>
    );
  }

  const result = analysis.result;
  return (
    <section className="mx-auto max-w-2xl space-y-5 rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary"><Leaf size={21} /></span>
        <div>
          <h2 className="text-xl font-semibold">Analysis {analysis.status}</h2>
          <p className="text-xs text-muted-foreground">Record {analysis.analysis_id}</p>
        </div>
      </div>

      {analysis.status === "failed" && (
        <div className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-destructive/5 p-4" role="status">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-destructive" />
          <div>
            <p className="text-sm">Inference failed. No diagnosis or severity result was saved for this scan.</p>
            {analysis.failure && <p className="mt-2 text-xs text-muted-foreground">{analysis.failure.message} (stage: {analysis.failure.stage}, code: {analysis.failure.code})</p>}
          </div>
        </div>
      )}
      {analysis.status === "pending" && (
        <div className="flex items-start gap-3 rounded-xl border border-border p-4" role="status">
          <Clock3 size={18} className="mt-0.5 shrink-0 text-muted-foreground" />
          <p className="text-sm">This scan is still pending and has no inference result yet.</p>
        </div>
      )}
      {assetError && <p className="rounded-lg border border-border p-3 text-xs text-muted-foreground" role="status">{assetError}</p>}
      {assetLinks.find((asset) => asset.kind === "original") && (
        <figure className="rounded-xl border border-border p-4">
          <figcaption className="mb-3 text-sm font-medium">Uploaded image</figcaption>
          {(() => {
            const original = assetLinks.find((asset) => asset.kind === "original");
            const source = original ? assetSources[original.storage_key] : undefined;
            return source ? <img src={source} alt="Uploaded plant image" className="max-h-96 w-full rounded-lg object-contain" /> : <p className="text-xs text-muted-foreground">Loading private image…</p>;
          })()}
        </figure>
      )}
      {result && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border p-4">
            <h3 className="font-semibold">Plant summary</h3>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div><dt className="text-muted-foreground">Health status</dt><dd>{result.plant_summary.health_status.replace(/_/g, " ")}</dd></div>
              <div><dt className="text-muted-foreground">Health score</dt><dd>{result.plant_summary.overall_health_score.toFixed(1)} / 100</dd></div>
              <div><dt className="text-muted-foreground">Leaves analyzed</dt><dd>{result.plant_summary.valid_leaves_analyzed} of {result.plant_summary.total_leaves_detected}</dd></div>
              <div><dt className="text-muted-foreground">Processing time</dt><dd>{result.processing_time_ms} ms ({result.hardware_device})</dd></div>
              {result.plant_summary.primary_diagnosis && <div><dt className="text-muted-foreground">Primary diagnosis</dt><dd>{result.plant_summary.primary_diagnosis}</dd></div>}
            </dl>
          </div>
          {result.leaves.map((leaf) => (
            <article key={leaf.leaf_id} className="rounded-xl border border-border p-4">
              <h3 className="font-semibold">Leaf {leaf.leaf_id + 1}</h3>
              {leaf.classification ? <p className="mt-2 text-sm">{leaf.classification.primary_class} · {(leaf.classification.confidence * 100).toFixed(1)}% confidence</p> : <p className="mt-2 text-sm text-muted-foreground">No classification result.</p>}
              {leaf.severity && <p className="mt-1 text-sm">Severity: {leaf.severity.status === "available" && leaf.severity.affected_percentage !== null ? `${leaf.severity.affected_percentage.toFixed(2)}% affected (${leaf.severity.level ?? "unrated"})` : "unavailable"}</p>}
              {leaf.prediction_uncertainty && <p className="mt-1 text-xs text-muted-foreground">Prediction uncertainty: {leaf.prediction_uncertainty.score.toFixed(3)}; calibration {leaf.prediction_uncertainty.calibration_status}.</p>}
              {leaf.ood && <p className="mt-1 text-xs text-muted-foreground">Provisional out-of-distribution warning: {leaf.ood.is_ood ? "flagged" : "not flagged"} ({leaf.ood.method}); this signal is not validated.</p>}
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {[
                  { label: "Leaf mask", asset: leaf.leaf_mask_asset },
                  { label: "Lesion mask", asset: leaf.segmentation?.mask_asset ?? null },
                  { label: "Classifier attention", asset: leaf.explainability?.heatmap_asset ?? null },
                ].map(({ label, asset }) => {
                  const source = asset ? assetSources[asset.storage_key] : undefined;
                  if (!asset || !source) return null;
                  return <figure key={`${leaf.leaf_id}-${label}`} className="rounded-lg border border-border p-2">
                    <figcaption className="mb-2 text-xs text-muted-foreground">{label}</figcaption>
                    <img src={source} alt={`${label} for leaf ${leaf.leaf_id + 1}`} loading="lazy" className="max-h-48 w-full rounded object-contain" />
                  </figure>;
                })}
              </div>
              {leaf.warnings.map((warning, index) => <p key={`${warning.code}-${index}`} className="mt-2 text-xs text-muted-foreground">{warning.message}</p>)}
            </article>
          ))}
          {result.warnings.map((warning, index) => <p key={`${warning.code}-${index}`} className="text-sm text-muted-foreground">{warning.message}</p>)}
          <p className="text-xs text-muted-foreground">Uncertainty and severity are reported according to the stored model result; provisional signals are not calibrated clinical or agronomic judgments.</p>
        </div>
      )}
      {analysis.status === "completed" && !result && (
        <p className="rounded-xl border border-destructive/40 p-4 text-sm" role="alert">The record is marked completed but contains no result. This response is inconsistent; no diagnosis is shown.</p>
      )}

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="text-muted-foreground">Created</dt><dd>{new Date(analysis.created_at).toLocaleString()}</dd></div>
        <div><dt className="text-muted-foreground">Image</dt><dd>{analysis.image_content_type} · {Math.ceil(analysis.image_size_bytes / 1024)} KB</dd></div>
        <div><dt className="text-muted-foreground">Result available</dt><dd>{analysis.result_available ? "Yes" : "No"}</dd></div>
      </dl>

      <div className="flex flex-wrap gap-3">
        <Button variant="outline" onClick={() => navigate("/scan")}>Save another image</Button>
        <Button variant="destructive" onClick={() => void deleteCurrentAnalysis()} disabled={isDeleting}>
          {isDeleting ? <Loader size={16} className="mr-2 animate-spin" /> : <Trash2 size={16} className="mr-2" />}
          Delete analysis
        </Button>
      </div>
    </section>
  );
}
