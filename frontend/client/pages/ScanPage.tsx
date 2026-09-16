import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ScanLine, Leaf, AlertTriangle, Loader, CheckCircle, Camera } from "lucide-react";
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
  const [analysisResult, setAnalysisResult] = useState<PlantAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error("Please upload an image file");
        return;
      }
      setImageFile(file);
      setError(null);
      setAnalysisResult(null);
    }
  };

  const handleScanClick = useCallback(async () => {
    if (!imageFile) {
      toast.error("Please select an image to scan");
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const response = await analysisApi.analyzeImage(imageFile);
      setIsProcessing(false);
      setAnalysisResult(response);

      // Navigate to results page with the analysis ID
      navigate(`/scan/results/${response.analysis_id}`);
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || "An error occurred during analysis");
      toast.error("Analysis failed: " + err.message);
    }
  }, [imageFile, navigate, analysisApi]);

  const handleRetakeClick = () => {
    setImageFile(null);
    setScanResult(null);
    setError(null);
  };

  if (analysisResult) {
    // Show results temporarily before redirecting
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-center space-x-3">
          <CheckCircle size={24} className="text-success" />
          <h2 className="text-xl font-semibold">Analysis Complete!</h2>
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
          Upload an image of your plant or use your camera to analyze leaf health
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
              disabled={isProcessing}
            />
            {imageFile && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <Loader size={24} className="text-muted-foreground/50" />
              </div>
            )}
          </div>
          {imageFile && (
            <div className="mt-3 flex items-center space-x-2 text-xs text-muted-foreground">
              <Leaf size={14} />
              <span>{imageFile.name}</span>
            </div>
          )}
        </div>

        {/* Or Camera Option */}
        <div className="border dashed border-border/60 rounded-xl p-6 text-center">
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
        <div className="flex flex-col sm:flex-row sm:space-x-3 w-full">
          <Button
            variant="outline"
            disabled={!imageFile || isProcessing}
            onClick={handleRetakeClick}
            className="w-full sm:w-auto"
          >
            {isProcessing ? "Processing..." : "Remove Image"}
          </Button>
          <Button
            className="w-full sm:w-auto"
            disabled={!imageFile || isProcessing}
            onClick={handleScanClick}
          >
            {isProcessing ? (
              <>
                <Loader size={16} className="mr-2" />
                Analyzing...
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

      {/* Error Message */}
      {error && (
        <div className="rounded-xl border border-destructive/50 bg-destructive/50 p-4">
          <AlertTriangle size={20} className="mr-3 h-4 w-4 text-destructive" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}