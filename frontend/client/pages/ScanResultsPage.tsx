import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AlertTriangle, Clock3, Leaf, Loader } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { AnalysisLifecycleResponse, ApiError, analysisApi } from "@/lib/api";

export default function ScanResultsPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { accessToken, logout } = useAuth();
  const [analysis, setAnalysis] = useState<AnalysisLifecycleResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <section className="mx-auto max-w-2xl space-y-5 rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary"><Leaf size={21} /></span>
        <div>
          <h2 className="text-xl font-semibold">Analysis {analysis.status}</h2>
          <p className="text-xs text-muted-foreground">Record {analysis.analysis_id}</p>
        </div>
      </div>

      <div className="flex items-start gap-3 rounded-xl border border-border p-4">
        <Clock3 size={18} className="mt-0.5 shrink-0 text-muted-foreground" />
        <div>
          <p className="font-medium">Image saved; diagnosis unavailable</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Real plant inference is not integrated. This record contains no disease, severity, confidence, or visualization results.
          </p>
        </div>
      </div>

      <dl className="grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="text-muted-foreground">Created</dt><dd>{new Date(analysis.created_at).toLocaleString()}</dd></div>
        <div><dt className="text-muted-foreground">Image</dt><dd>{analysis.image_content_type} · {Math.ceil(analysis.image_size_bytes / 1024)} KB</dd></div>
        <div><dt className="text-muted-foreground">Result available</dt><dd>{analysis.result_available ? "Yes" : "No"}</dd></div>
      </dl>

      <Button variant="outline" onClick={() => navigate("/scan")}>Save another image</Button>
    </section>
  );
}
