import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, Clock3, Loader, ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { AnalysisLifecycleResponse, ApiError, analysisApi } from "@/lib/api";

export default function HistoryPage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<AnalysisLifecycleResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadHistory() {
      if (!accessToken) {
        setError("Sign in to view your saved analyses.");
        setIsLoading(false);
        return;
      }
      try {
        const records = await analysisApi.getAnalyses(accessToken);
        if (active) setAnalyses(records);
      } catch (caught) {
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          navigate("/login", { replace: true });
          return;
        }
        if (active) setError(caught instanceof Error ? caught.message : "Could not load scan history.");
      } finally {
        if (active) setIsLoading(false);
      }
    }
    void loadHistory();
    return () => { active = false; };
  }, [accessToken, logout, navigate]);

  if (isLoading) return <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground"><Loader size={18} className="animate-spin" />Loading your analyses…</p>;

  return (
    <section className="mx-auto max-w-3xl space-y-5">
      <header><h2 className="text-2xl font-semibold">Your saved analyses</h2><p className="mt-1 text-sm text-muted-foreground">Only analyses belonging to your account are listed.</p></header>
      {error && <div className="flex items-center gap-2 rounded-xl border border-destructive/40 p-4 text-sm text-destructive" role="alert"><AlertTriangle size={18} />{error}</div>}
      {!error && analyses.length === 0 && (
        <div className="rounded-2xl border border-border bg-card p-8 text-center">
          <ScanLine size={26} className="mx-auto text-muted-foreground" />
          <h3 className="mt-3 font-semibold">No saved analyses yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">Save a validated plant image to create your first record.</p>
          <Button asChild className="mt-4"><Link to="/scan">Save a plant image</Link></Button>
        </div>
      )}
      <div className="space-y-3">
        {analyses.map((analysis) => (
          <Link key={analysis.analysis_id} to={`/scan/results/${analysis.analysis_id}`} className="flex items-center justify-between gap-4 rounded-xl border border-border bg-card p-4 transition hover:bg-muted/40">
            <div className="min-w-0"><p className="truncate text-sm font-medium">Analysis {analysis.analysis_id.slice(0, 8)}</p><p className="mt-1 text-xs text-muted-foreground">{analysis.image_content_type} · {new Date(analysis.created_at).toLocaleString()}</p></div>
            <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs"><Clock3 size={13} />{analysis.status}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
