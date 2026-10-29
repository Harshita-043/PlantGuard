import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertTriangle, Clock3, Loader, RefreshCw, ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { AnalysisLifecycleResponse, ApiError, analysisApi, plantsApi } from "@/lib/api";
import type { PlantResponse } from "@shared/api";

const PAGE_SIZE = 10;

export default function HistoryPage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<AnalysisLifecycleResponse[]>([]);
  const [plants, setPlants] = useState<PlantResponse[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [plantFilter, setPlantFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFirstPage = useCallback(async () => {
    if (!accessToken) {
      setError("Sign in to view your saved analyses.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [records, userPlants] = await Promise.all([
        analysisApi.getAnalyses(accessToken, 0, PAGE_SIZE),
        plantsApi.getPlants(accessToken),
      ]);
      setAnalyses(records);
      setPlants(userPlants);
      setHasMore(records.length === PAGE_SIZE);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "Could not load scan history.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, logout, navigate]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const loadMore = async () => {
    if (!accessToken || isLoadingMore || !hasMore) return;
    setIsLoadingMore(true);
    setError(null);
    try {
      const next = await analysisApi.getAnalyses(accessToken, analyses.length, PAGE_SIZE);
      setAnalyses((current) => [...current, ...next]);
      setHasMore(next.length === PAGE_SIZE);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(caught instanceof Error ? caught.message : "More scan history could not be loaded.");
    } finally {
      setIsLoadingMore(false);
    }
  };

  const visibleAnalyses = useMemo(() => {
    const query = search.trim().toLowerCase();
    return analyses.filter((analysis) => {
      if (statusFilter !== "all" && analysis.status !== statusFilter) return false;
      if (plantFilter === "unassigned" && analysis.plant_id !== null) return false;
      if (plantFilter !== "all" && plantFilter !== "unassigned" && analysis.plant_id !== plantFilter) return false;
      if (!query) return true;
      const diagnosis = analysis.result?.plant_summary.primary_diagnosis ?? "";
      return `${analysis.analysis_id} ${diagnosis}`.toLowerCase().includes(query);
    });
  }, [analyses, plantFilter, search, statusFilter]);

  if (isLoading) {
    return (
      <p className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground" role="status">
        <Loader size={18} className="animate-spin" />Loading your analyses…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-4xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Your saved analyses</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Persisted scans associated with your account.
          </p>
        </div>
        <Button variant="outline" onClick={() => void loadFirstPage()}>
          <RefreshCw size={15} className="mr-2" />Refresh
        </Button>
      </header>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/40 p-4 text-sm text-destructive" role="alert">
          <AlertTriangle size={18} />{error}
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="grid gap-1 text-xs text-muted-foreground">
          Search scan ID or diagnosis
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
          />
        </label>
        <label className="grid gap-1 text-xs text-muted-foreground">
          Status
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
          >
            <option value="all">All statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>
        </label>
        <label className="grid gap-1 text-xs text-muted-foreground">
          Plant
          <select
            value={plantFilter}
            onChange={(event) => setPlantFilter(event.target.value)}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
          >
            <option value="all">All plants</option>
            <option value="unassigned">Unassigned</option>
            {plants.map((plant) => <option key={plant.id} value={plant.id}>{plant.name}</option>)}
          </select>
        </label>
      </div>

      {analyses.length === 0 ? (
        <div className="rounded-2xl border border-border bg-card p-8 text-center">
          <ScanLine size={26} className="mx-auto text-muted-foreground" />
          <h3 className="mt-3 font-semibold">No saved analyses yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">Save a validated plant image to create your first record.</p>
          <Button asChild className="mt-4"><Link to="/scan">Save a plant image</Link></Button>
        </div>
      ) : visibleAnalyses.length === 0 ? (
        <p className="rounded-xl border border-border bg-card p-6 text-center text-sm text-muted-foreground">
          No saved scans match these filters.
        </p>
      ) : (
        <div className="space-y-3">
          {visibleAnalyses.map((analysis) => {
            const plant = plants.find((item) => item.id === analysis.plant_id);
            return (
              <Link
                key={analysis.analysis_id}
                to={`/scan/results/${encodeURIComponent(analysis.analysis_id)}`}
                className="flex items-center justify-between gap-4 rounded-xl border border-border bg-card p-4 transition hover:bg-muted/40"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    Analysis {analysis.analysis_id.slice(0, 8)}
                    {plant && <span className="ml-2 text-xs text-muted-foreground">· {plant.name}</span>}
                  </p>
                  <p className="mt-1 truncate text-xs text-muted-foreground">
                    {analysis.result?.plant_summary.primary_diagnosis ?? analysis.failure?.message ?? analysis.image_content_type}
                    {" · "}{new Date(analysis.created_at).toLocaleString()}
                  </p>
                </div>
                <span className="flex shrink-0 items-center gap-1.5 rounded-full bg-muted px-3 py-1 text-xs">
                  <Clock3 size={13} />{analysis.status}
                </span>
              </Link>
            );
          })}
        </div>
      )}

      {hasMore && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={() => void loadMore()} disabled={isLoadingMore}>
            {isLoadingMore && <Loader size={15} className="mr-2 animate-spin" />}
            Load more scans
          </Button>
        </div>
      )}
    </section>
  );
}
