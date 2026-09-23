import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ScanLine, Leaf, AlertTriangle, CheckCircle, Loader, Camera, Info, CircleHelp, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Toaster, toast } from "@/components/ui/toaster";
import { analysisApi, PlantAnalysisResponse, LeafResult, PlantHealthSummary } from "@/lib/api";

export default function ScanPage() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<PlantAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [workflowStep, setWorkflowStep] = useState<number>(0);
  const navigate = useNavigate();

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error("Please upload an image file");
        return;
      }
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast.error("File size too large. Maximum 10MB allowed.");
        return;
      }
      setImageFile(file);
      setError(null);
      setAnalysisResult(null);
      setWorkflowStep(1); // Step 1: Upload whole-plant image (complete)
    }
  };

  const handleScanClick = useCallback(async () => {
    if (!imageFile) {
      toast.error("Please select an image to scan");
      return;
    }

    setIsProcessing(true);
    setIsAnalyzing(true);
    setError(null);
    setUploadProgress(0);
    setWorkflowStep(1);

    try {
      // Simulate upload progress (in a real app, we'd use actual upload progress events)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => Math.min(prev + 10, 90));
      }, 100);

      const response = await analysisApi.analyzeImage(imageFile);

      clearInterval(progressInterval);
      setUploadProgress(100);
      setWorkflowStep(8); // Complete

      setIsProcessing(false);
      setIsAnalyzing(false);
      setAnalysisResult(response);

      // Navigate to results page after 2-second delay to show results temporarily
      setTimeout(() => {
        navigate(`/scan/results/${response.analysis_id}`);
      }, 2000);
    } catch (err: any) {
      setIsProcessing(false);
      setIsAnalyzing(false);
      setWorkflowStep(0);
      setError(err.message || "An error occurred during analysis");
      toast.error("Analysis failed: " + err.message);
    }
  }, [imageFile, navigate, analysisApi]);

  const handleRetakeClick = () => {
    setImageFile(null);
    setAnalysisResult(null);
    setError(null);
    setIsProcessing(false);
    setIsAnalyzing(false);
    setUploadProgress(0);
    setWorkflowStep(0);
  };

  if (analysisResult) {
    // Show results temporarily before redirecting
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center space-x-3">
          <CheckCircle size={24} className="text-success" />
          <h2 className="text-xl font-semibold">Analysis Complete!</h2>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-center">
            <div className="flex items-center space-x-3">
              <div className={`w-8 h-8 rounded-full ${analysisResult.plant_health_summary.health_status === "excellent"
                ? "bg-[hsl(var(--success)/.20)] text-[hsl(var(--success))]"
                : analysisResult.plant_health_summary.health_status === "good"
                ? "bg-[hsl(var(--success)/.12)] text-[hsl(var(--success))]"
                : analysisResult.plant_health_summary.health_status === "fair"
                ? "bg-[hsl(var(--warning)/.12)] text-[hsl(var(--warning))]"
                : analysisResult.plant_health_summary.health_status === "poor"
                ? "bg-[hsl(var(--destructive)/.12)] text-[hsl(var(--destructive))]"
                : "bg-[hsl(var(--muted)/.12)] text-[hsl(var(--muted))]"
              }">
                {analysisResult.plant_health_summary.health_status.charAt(0).toUpperCase() + analysisResult.plant_health_summary.health_status.slice(1)}
              </div>
              <div className="text-center">
                <h3 className="text-lg font-semibold">{analysisResult.plant_health_summary.health_status.charAt(0).toUpperCase() + analysisResult.plant_health_summary.health_status.slice(1)} Health</h3>
                <p className="text-sm text-muted-foreground">
                  Score: {Math.round(analysisResult.plant_health_summary.overall_health_score)}/100
                </p>
              </div>
            </div>
          </div>
          <p className="text-center text-sm text-muted-foreground">
            Analyzed {analysisResult.leaf_results.length} leaf{analysisResult.leaf_results.length !== 1 ? 's' : ''}
          </p>
          <p className="text-center text-sm text-muted-foreground">
            {analysisResult.ml_mode === "mock"
              ? "(Using mock ML models for development)"
              : "(Using real ML models)"}
          </p>
        </div>
        <p className="text-muted-foreground">
          Your plant analysis has been processed. Redirecting to results...
        </p>
        <div className="flex justify-center">
          <Button variant="outline" onClick={handleRetakeClick}>
            Scan Another Plant
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center text-center">
        <div className="flex items-center justify-center w-[80px] h-[80px] rounded-xl bg-primary/10 text-primary mb-4">
          <ScanLine size={24} />
        </div>
        <h2 className="text-2xl font-semibold tracking-[-0.05em]">Scan Plant for Health Analysis</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Upload an image of your plant to analyze leaf health
        </p>
      </div>

      <div className="space-y-4">
        {/* Image Upload Section */}
        <div className="space-y-3">
          <Label htmlFor="image-upload" className="text-sm font-medium">
            Plant Image
          </Label>
          <div className="relative">
            <input
              id="image-upload"
              type="file"
              accept="image/*"
              className="block w-full text-sm text-muted-foreground file:cursor-pointer file:text-sm file:font-medium file:bg-primary file:text-primary-foreground file:hover:bg-primary/80"
              onChange={handleImageChange}
              disabled={isProcessing || isAnalyzing}
            />
            {imageFile && (
              <div className="mt-2 flex items-center space-x-2 text-xs text-muted-foreground">
                <Leaf size={14} />
                <span>{imageFile.name}</span> ({Math.round(imageFile.size / 1024)} KB)
              </div>
            )}
            {!imageFile && (
              <div className="text-xs text-muted-foreground mt-2">
                Supported formats: JPG, PNG
              </div>
            )}
            {isProcessing && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 rounded border border-dashed" style={{ borderColor: "hsl(var(--primary))" }}></div>
                  <span className="ml-2">Preparing upload...</span>
                </div>
              </div>
            )}
            {isAnalyzing && !isProcessing && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 rounded border border-dashed" style={{ borderColor: "hsl(var(--primary))" }}></div>
                  <span className="ml-2">Analyzing image...</span>
                </div>
              </div>
            )}
            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-full h-4 bg-[hsl(var(--background))] rounded-full">
                  <div className={`h-4 bg-[hsl(var(--primary))] rounded-full` style={{ width: uploadProgress + '%' }}></div>
                </div>
                <div className="text-center text-xs mt-1">Uploading... {uploadProgress}%</div>
              </div>
            )}
          </div>
        </div>

        {/* Analysis Workflow Info */}
        <div className="border border-border/80 rounded-xl p-4 mt-4">
          <h3 className="text-[16px] font-semibold tracking-[-0.02em]">Analysis Workflow</h3>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              {workflowStep >= 1 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">1. Upload whole-plant image</p>
                <p className="text-sm text-muted-foreground">
                  No manual leaf cropping required
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 2 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">2. Image validation</p>
                <p className="text-sm text-muted-foreground">
                  Checks file type and size (max 10MB)
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 3 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">3. Analysis request</p>
                <p className="text-sm text-muted-foreground">
                  Sent to backend for processing
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 4 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">4. Processing state</p>
                <p className="text-sm text-muted-foreground">
                  Leaf segmentation → classification → severity → explainability
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 5 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">5. Leaf segmentation service</p>
                <p className="text-sm text-muted-foreground">
                  Detects all leaves in the image (dynamic count)
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 6 ? (
                <CheckCircle size={14} className="text-success" />
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">6. Per-leaf analysis</p>
                <p className="text-sm text-muted-foreground">
                  Each leaf analyzed for disease, severity, and explainability
                </p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              {workflowStep >= 7 ? (
                <CheckCircle size={14} className="text-success" )
              ) : (
                <CircleHelp size={14} className="text-muted-foreground" />
              )}
              <div className="space-y-1">
                <p className="font-medium">7. Plant-level result</p>
                <p className="text-sm text-muted-foreground">
                  Aggregated health score and recommendations
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Or Camera Option */}
        <div className="border dashed border-border/60 rounded-xl p-6 text-center mt-4">
          <div className="flex items-center justify-center space-x-3 mb-3">
            <Camera size={20} className="text-muted-foreground" />
            <span className="text-sm font-medium">Or use camera</span>
          </div>
          <p className="text-xs text-muted-foreground">
            Click to capture image from your device camera
          </p>
          <Button variant="ghost" size="icon" onClick={() => toast.info("Camera functionality coming soon")}>
            <Camera size={24} />
          </Button>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row sm:space-x-3 w-full mt-4">
          <Button
            variant="outline"
            disabled={!imageFile || isProcessing || isAnalyzing}
            onClick={handleRetakeClick}
            className="w-full sm:w-auto"
          >
            {isProcessing || isAnalyzing ? (
              <>
                <Loader size={16} className="mr-2" />
                {isProcessing ? "Processing..." : "Analyzing..."}
              </>
            ) : (
              <>
                <Leaf size={16} className="mr-2" />
                Remove Image
              </>
            )}
          </Button>
          <Button
            className="w-full sm:w-auto"
            disabled={!imageFile || isProcessing || isAnalyzing}
            onClick={handleScanClick}
          >
            {isProcessing || isAnalyzing ? (
              <>
                <Loader size={16} className="mr-2" />
                {isProcessing ? "Processing..." : "Analyzing..."}
              </>
            ) : (
              <>
                <ScanLine size={16} className="mr-2" />
                Scan Plant
              </>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/50 bg-destructive/50 p-4">
          <AlertTriangle size={20} className="mr-3 h-4 w-4 text-destructive" />
          <span>{error}</span>
        </div>
      )}

      {/* Special States */}
      {imageFile && !isProcessing && !isAnalyzing && analysisResult === null && (
        <div className="space-y-4">
          {/* Empty/No-leaf state would be handled in results page */}
          {/* Low-quality image state would be detected by backend and returned as error */}
          <div className="text-center text-sm text-muted-foreground">
            Ready to analyze your plant image. The system will automatically detect and analyze all leaves.
          </div>
        </div>
      )}
    </div>
  );
}