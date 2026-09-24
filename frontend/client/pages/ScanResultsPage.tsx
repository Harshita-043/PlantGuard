import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Leaf, AlertTriangle, CheckCircle, Loader, RefreshCw, TrendingUp, FileText, Settings, CircleHelp, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { toast } from "@/hooks/use-toast";
import { analysisApi, PlantAnalysisResponse, LeafResult, PlantHealthSummary } from "@/lib/api";

export default function ScanResultsPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const [analysisResult, setAnalysisResult] = useState<PlantAnalysisResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalysisData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch detailed analysis results
        const result = await analysisApi.getAnalysis(scanId);
        setAnalysisResult(result);
      } catch (err: any) {
        setError(err.message || "Failed to load analysis results");
        toast({ title: "Could not load analysis results", description: err.message });
      } finally {
        setIsLoading(false);
      }
    };

    if (scanId) {
      fetchAnalysisData();
    }
  }, [scanId, navigate]);

  const handleRescanClick = () => {
    navigate(`/scan`);
  };

  const handleViewRecommendationsClick = () => {
    navigate(`/recommendations/${scanId}`);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Loader size={32} className="mb-4" />
          <h2 className="text-xl font-semibold">Loading analysis results...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={32} className="mb-4 text-destructive" />
          <h2 className="text-xl font-semibold">Error loading results</h2>
          <p className="text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={handleRescanClick}>
            Go Back to Scan
          </Button>
        </div>
      </div>
    );
  }

  if (!analysisResult) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Loader size={32} className="mb-4" />
          <h2 className="text-xl font-semibold">Preparing results...</h2>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col items-center justify-center text-center">
        <div className="flex items-center justify-circle space-x-3">
          <CheckCircle size={24} className="text-success" />
          <h2 className="text-2xl font-semibold tracking-[-0.05em]">Analysis Complete</h2>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Analysis of plant scan #{analysisResult.analysis_id.substring(0, 8)}
        </p>
      </div>

      {/* Health Overview */}
      <div className="grid gap-4 sm:grid-cols-[1.2fr_1fr]">
        {/* Health Score Ring */}
        <div className="relative shrink-0">
          <div className="flex items-center justify-center">
            <div className="relative shrink-0" style={{ width: 120, height: 120 }}>
              <svg className="-rotate-90" width={120} height={120} viewBox="0 0 120 120">
                <circle cx={60} cy={60} r={50} fill="none" stroke="hsl(var(--border))" strokeWidth={8} />
                <circle
                  cx={60}
                  cy={60}
                  r={50}
                  fill="none"
                  stroke="hsl(var(--success))"
                  strokeLinecap="round"
                  strokeWidth={8}
                  strokeDasharray={314}
                  strokeDashoffset={314 * (1 - analysisResult.plant_health_summary.overall_health_score / 100)}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold tracking-[-0.06em] text-foreground">
                  {Math.round(analysisResult.plant_health_summary.overall_health_score)}
                </span>
                <span className="text-[10px] font-medium text-muted-foreground">/ 100</span>
              </div>
            </div>
          </div>
          <p className="mt-4 text-xs font-bold uppercase tracking-[0.18em] text-[hsl(var(--ai-accent))]">
            Plant Health Score
          </p>
        </div>

        {/* Health Status and Recommendations */}
        <div className="space-y-4">
          <div className="flex items-start justify-between space-x-3">
            <div className="flex items-center gap-2">
              <div className={`grid size-5 place-items-center rounded-xl ${
                analysisResult.plant_health_summary.health_status === "excellent"
                  ? "bg-[hsl(var(--success)/.20)] text-[hsl(var(--success))]"
                  : analysisResult.plant_health_summary.health_status === "good"
                  ? "bg-[hsl(var(--success)/.12)] text-[hsl(var(--success))]"
                  : analysisResult.plant_health_summary.health_status === "fair"
                  ? "bg-[hsl(var(--warning)/.12)] text-[hsl(var(--warning))]"
                  : analysisResult.plant_health_summary.health_status === "poor"
                  ? "bg-[hsl(var(--destructive)/.12)] text-[hsl(var(--destructive))]"
                  : "bg-[hsl(var(--muted)/.12)] text-[hsl(var(--muted))]"
              }`}>
                {analysisResult.plant_health_summary.health_status.charAt(0).toUpperCase() + analysisResult.plant_health_summary.health_status.slice(1)}
              </div>
              <div>
                <h3 className="text-lg font-semibold">{analysisResult.plant_health_summary.health_status.charAt(0).toUpperCase() + analysisResult.plant_health_summary.health_status.slice(1)} Health</h3>
                <p className="text-sm text-muted-foreground">
                  Based on analysis of {analysisResult.leaf_results.length} leaves
                </p>
              </div>
            </div>
            <Button variant="outline" onClick={handleViewRecommendationsClick}>
              View Recommendations <ChevronRight size={16} />
            </Button>
          </div>

          {/* Disease Summary */}
          <div className="border border-border/80 rounded-xl p-4">
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-sm font-semibold text-muted-foreground">Disease Summary</h3>
              <span className="text-xs font-medium">
                {analysisResult.leaf_results.length} leaves analyzed
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span>Healthy Leaves:</span>
                <span className="font-mono">{analysisResult.plant_health_summary.healthy_leaf_count}/{analysisResult.plant_health_summary.total_leaf_count}</span>
              </div>
              {Object.entries(analysisResult.plant_health_summary.disease_summary).map(([disease, count]) => (
                disease !== "healthy" && (
                  <div key={disease} className="flex items-center justify-between text-xs">
                    <span>{disease.replace('_', ' ').toLowerCase()}:</span>
                    <span className="font-mono text-[hsl(var(--warning))]">{count}</span>
                  </div>
                )
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Scan media</h3>

        <div className="rounded-xl border border-border/80 p-4 text-sm text-muted-foreground">
          The API does not retain or return the original scan image, so image overlays are unavailable.
        </div>
      </div>

      {/* Leaf Analysis Details */}
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Leaf Analysis Details</h3>
          <Button variant="ghost" size="icon" onClick={() => toast({ title: "Leaf visualization is unavailable" })}>
            <Settings size={20} />
          </Button>
        </div>

        {analysisResult.leaf_results.map((leaf, index) => (
          <div key={leaf.leaf_index} className="border border-border/80 rounded-xl p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <Leaf size={16} className={leaf.disease_class === "healthy"
                  ? "text-[hsl(var(--success))]"
                  : "text-[hsl(var(--warning))]"
                } />
                <div>
                  <p className="text-sm font-medium">Leaf #{leaf.leaf_index + 1}</p>
                  <p className="text-xs text-muted-foreground">{leaf.disease_class.replace('_', ' ').toLowerCase()}</p>
                </div>
              </div>
              <div className="text-xs font-medium">
                {leaf.classification_confidence * 100}% confidence
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground">Severity</p>
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: leaf.severity_score * 100 + "%",
                      backgroundColor:
                        leaf.severity_level === "low"
                          ? "var(--success)"
                          : leaf.severity_level === "medium"
                            ? "var(--warning)"
                            : "var(--destructive)",
                    }}
                  />
                  <span className="text-xs">{Math.round(leaf.severity_score * 100)}%</span>
                </div>
                <p className="text-xs text-muted-foreground">{leaf.severity_level} severity</p>
              </div>

              <div className="space-y-1">
                <p className="text-xs font-semibold text-muted-foreground">Classification</p>
                <p className="text-xs">{leaf.disease_class.replace('_', ' ').toLowerCase()}</p>
                <p className="text-xs text-muted-foreground">{leaf.classification_confidence * 100}% confidence</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:space-x-3 w-full">
        <Button
          variant="outline"
          onClick={handleRescanClick}
          className="w-full sm:w-auto"
        >
          <Leaf size={16} className="mr-2" />
          Scan Another Plant
        </Button>
        <Button
          onClick={handleViewRecommendationsClick}
          className="w-full sm:w-auto"
        >
          <FileText size={16} className="mr-2" />
          View Recommendations
        </Button>
      </div>
    </div>
  );
}
