import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Leaf,
  Loader,
  RefreshCw,
  ScanLine,
  Sprout,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthContext";
import { ApiError, dashboardApi } from "@/lib/api";
import type { DashboardMetricsResponse } from "@shared/api";

const metricCards = [
  { key: "total_analyses", label: "Total scans" },
  { key: "healthy_analyses", label: "Healthy" },
  { key: "diseased_analyses", label: "Diseased" },
  { key: "inconclusive_analyses", label: "Inconclusive" },
  { key: "failed_analyses", label: "Failed" },
] as const;

export default function Index() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<DashboardMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    if (!accessToken) {
      setError("Sign in to view your dashboard.");
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setMetrics(await dashboardApi.getMetrics(accessToken));
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      setError(
        caught instanceof Error
          ? caught.message
          : "Dashboard metrics could not be loaded.",
      );
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, logout, navigate]);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  if (isLoading && !metrics) {
    return (
      <p className="flex items-center justify-center gap-2 py-20 text-sm text-muted-foreground" role="status">
        <Loader size={18} className="animate-spin" />
        Loading your dashboard…
      </p>
    );
  }

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.04em]">
            Your plant health
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Metrics from analyses saved to your account.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void loadMetrics()} disabled={isLoading}>
            <RefreshCw size={15} className={`mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button asChild>
            <Link to="/scan"><ScanLine size={16} className="mr-2" />New scan</Link>
          </Button>
        </div>
      </header>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/40 p-4 text-sm text-destructive" role="alert">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}

      {metrics && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {metricCards.map(({ key, label }) => (
              <article key={key} className="rounded-2xl border border-border bg-card p-4">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="mt-2 text-2xl font-semibold">{metrics[key]}</p>
              </article>
            ))}
            <article className="rounded-2xl border border-border bg-card p-4">
              <p className="text-xs text-muted-foreground">Tracked plants</p>
              <p className="mt-2 flex items-center gap-2 text-2xl font-semibold">
                <Sprout size={20} className="text-primary" />
                {metrics.total_plants}
              </p>
            </article>
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-2xl border border-border bg-card p-5">
              <h3 className="font-semibold">Recent scans</h3>
              {metrics.recent_scans.length ? (
                <ul className="mt-3 divide-y divide-border">
                  {metrics.recent_scans.map((scan) => (
                    <li key={scan.analysis_id}>
                      <Link
                        to={`/scan/results/${encodeURIComponent(scan.analysis_id)}`}
                        className="flex items-center justify-between gap-4 py-3 hover:text-primary"
                      >
                        <span className="flex min-w-0 items-center gap-2">
                          <Leaf size={16} className="shrink-0" />
                          <span className="truncate text-sm">
                            Scan {scan.analysis_id.slice(0, 8)}
                          </span>
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {scan.status} · {new Date(scan.created_at).toLocaleDateString()}
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  No saved scans yet. Start by uploading a plant image.
                </p>
              )}
              {metrics.total_analyses === 0 && (
                <Button asChild variant="outline" className="mt-4">
                  <Link to="/scan">Create your first scan</Link>
                </Button>
              )}
            </section>

            <section className="rounded-2xl border border-border bg-card p-5">
              <h3 className="font-semibold">Health trend</h3>
              {metrics.health_trend.length ? (
                <div className="mt-4 flex h-40 items-end gap-2 border-b border-l border-border px-2">
                  {metrics.health_trend.map((point) => (
                    <Link
                      key={point.analysis_id}
                      to={`/scan/results/${encodeURIComponent(point.analysis_id)}`}
                      className="group flex h-full min-w-0 flex-1 flex-col justify-end"
                      title={`${point.health_score.toFixed(1)} / 100 · ${new Date(point.timestamp).toLocaleDateString()}`}
                      aria-label={`Health score ${point.health_score.toFixed(1)} out of 100 on ${new Date(point.timestamp).toLocaleDateString()}`}
                    >
                      <span
                        className="min-h-1 rounded-t bg-primary/75 transition group-hover:bg-primary"
                        style={{ height: `${point.health_score}%` }}
                      />
                      <span className="mt-1 truncate text-center text-[10px] text-muted-foreground">
                        {new Date(point.timestamp).toLocaleDateString(undefined, { month: "numeric", day: "numeric" })}
                      </span>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  Health trends appear after a completed scan has a valid score.
                </p>
              )}
              <p className="mt-3 text-xs text-muted-foreground">
                Average recorded score:{" "}
                {metrics.average_health_score === null
                  ? "unavailable"
                  : `${metrics.average_health_score.toFixed(1)} / 100`}
              </p>
            </section>
          </div>

          <section className="rounded-2xl border border-border bg-card p-5">
            <h3 className="font-semibold">Disease distribution</h3>
            {Object.keys(metrics.disease_distribution).length ? (
              <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(metrics.disease_distribution)
                  .sort(([, first], [, second]) => second - first)
                  .map(([label, count]) => (
                    <li key={label} className="flex justify-between gap-3 rounded-lg bg-muted/50 px-3 py-2 text-sm">
                      <span className="truncate">{label}</span>
                      <span className="font-medium">{count}</span>
                    </li>
                  ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">
                No persisted disease classifications to summarize.
              </p>
            )}
          </section>
        </>
      )}
    </section>
  );
}
