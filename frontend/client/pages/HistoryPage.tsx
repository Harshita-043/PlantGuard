import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Leaf, AlertTriangle, CheckCircle, Loader, RefreshCw, TrendingUp, FileText, Settings, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Toaster, toast } from "@/components/ui/toaster";
import { analysisApi, PlantAnalysisResponse, LeafResult, PlantHealthSummary } from "@/lib/api";
import { Pagination } from "@/components/ui/pagination";

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState<PlantAnalysisResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAnalyses = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const skip = page * itemsPerPage;
        const result = await analysisApi.getAnalyses(skip, itemsPerPage);
        setAnalyses(result);
      } catch (err: any) {
        setError(err.message || "Failed to load analysis history");
        toast.error("Error loading history: " + err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnalyses();
  }, [page, itemsPerPage]);

  const handleViewDetails = (analysisId: string) => {
    navigate(`/scan/results/${analysisId}`);
  };

  const handleRescan = (analysis: PlantAnalysisResponse) => {
    // In a real app, we would need the original image/video to rescan
    // For now, we'll just show a message
    toast.info("Rescan functionality would require storing the original media");
  };

  const handleDelete = (analysisId: string) => {
    // In a real app, this would call a delete API
    toast.warning("Delete functionality not yet implemented");
  };

  const handleNextPage = () => {
    setPage(page + 1);
  };

  const handlePrevPage = () => {
    if (page > 0) {
      setPage(page - 1);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Loader size={32} className="mb-4" />
          <h2 className="text-xl font-semibold">Loading history...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <AlertTriangle size={32} className="mb-4 text-destructive" />
          <h2 className="text-xl font-semibold">Error loading history</h2>
          <p className="text-muted-foreground">{error}</p>
          <Button variant="outline" onClick={() => setPage(0)}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (analyses.length === 0 && page === 0) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <Leaf size={48} className="mb-4 text-muted-foreground" />
          <h2 className="text-xl font-semibold">No scans yet</h2>
          <p className="text-muted-foreground">
            Start by scanning a plant to see your history here.
          </p>
          <Button variant="default" onClick={() => navigate("/scan")}>
            Scan Your First Plant
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col items-center justify-center">
        <h2 className="text-2xl font-semibold tracking-[-0.05em]">Scan History</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Your previous plant analyses
        </p>
      </div>

      {/* Analyses List */}
      <div className="space-y-4">
        {analyses.map((analysis) => (
          <div key={analysis.analysis_id} className="border border-border/80 rounded-xl p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <Leaf size={20} className="text-[hsl(var(--primary))]" />
                <div>
                  <h3 className="text-lg font-semibold">Plant Analysis</h3>
                  <p className="text-sm text-muted-foreground">
                    {new Date(analysis.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className={`text-[hsl(var(${
                  analysis.plant_health_summary.health_status === "excellent"
                    ? "success"
                    : analysis.plant_health_summary.health_status === "good"
                    ? "success"
                    : analysis.plant_health_summary.health_status === "fair"
                    ? "warning"
                    : analysis.plant_health_summary.health_status === "poor"
                    ? "destructive"
                    : "muted"
                }))] font-bold`}>
                  {Math.round(analysis.plant_health_summary.overall_health_score)}%
                </div>
                <p className="text-xs text-muted-foreground">
                  Health Score
                </p>
              </div>
            </div>

            <div className="mt-4">
              <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Results Summary</h3>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="border border-border/80 rounded-xl p-3">
                  <p className="text-xs font-medium text-muted-foreground">Leaves Analyzed</p>
                  <p className="text-2xl font-bold">{analysis.leaf_results.length}</p>
                </div>
                <div className="border border-border/80 rounded-xl p-3">
                  <p className="text-xs font-medium text-muted-foreground">Healthy Leaves</p>
                  <p className="text-2xl font-bold">{analysis.plant_health_summary.healthy_leaf_count}</p>
                </div>
                <div className="border border-border/80 rounded-xl p-3">
                  <p className="text-xs font-medium text-muted-foreground">Diseased Leaves</p>
                  <p className="text-2xl font-bold">
                    {analysis.leaf_results.filter(l => l.disease_class !== "healthy").length}
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-start justify-between">
              <Button
                variant="outline"
                onClick={() => handleViewDetails(analysis.analysis_id)}
                className="flex-1 mr-2"
              >
                <FileText size={16} className="mr-2" />
                View Details
              </Button>
              <Button
                variant="ghost"
                onClick={() => handleRescan(analysis)}
                className="flex-1 ml-2"
              >
                <RefreshCw size={16} className="mr-2" />
                Rescan
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      {analyses.length > 0 && (
        <div className="flex justify-center">
          <Pagination
            page={page}
            onPageChange={handlePrevPage}
            onNextPageClick={handleNextPage}
            hasMore={analyses.length === 10} // Simple check - in real app would know total count
          />
        </div>
      )}
    </div>
  );
}