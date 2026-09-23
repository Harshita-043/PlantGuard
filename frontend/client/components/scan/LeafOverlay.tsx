import { useState } from "react";
import { Loader } from "lucide-react";
import { LeafResult } from "@/shared/api";

interface LeafOverlayProps {
  imageUrl: string;
  leafResults: LeafResult[];
  showDiseaseRegions: boolean;
  showGradCAM: boolean;
}

export default function LeafOverlay({
  imageUrl,
  leafResults,
  showDiseaseRegions = true,
  showGradCAM = false,
}: LeafOverlayProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageWidth, setImageWidth] = useState(0);
  const [imageHeight, setImageHeight] = useState(0);

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.target as HTMLImageElement;
    setImageWidth(img.width);
    setImageHeight(img.height);
    setImageLoaded(true);
  };

  if (!imageLoaded || imageWidth === 0 || imageHeight === 0) {
    return (
      <div className="w-full h-96 flex items-center justify-center">
        <Loader size={32} className="mb-4" />
        <p className="text-muted-foreground">Loading plant image...</p>
      </div>
    );
  }

  const leafElements = leafResults.map((leaf, index) => {
    // Convert normalized bounding box to pixel values
    const left = (leaf.bounding_box[0] * imageWidth) + "px";
    const top = (leaf.bounding_box[1] * imageHeight) + "px";
    const width = (leaf.bounding_box[2] * imageWidth) + "px";
    const height = (leaf.bounding_box[3] * imageHeight) + "px";

    // Determine leaf color based on disease status
    const isHealthy = leaf.disease_class === "healthy";
    const leafColor = isHealthy
      ? "hsl(var(--success))"
      : leaf.disease_class.includes("spot") || leaf.disease_class.includes("mildew")
      ? "hsl(var(--warning))"
      : "hsl(var(--destructive))";

    return (
      <div
        key={index}
        className="absolute"
        style={{ left, top, width, height, pointerEvents: "none" }}
      >
        {/* Leaf bounding box */}
        <div className="absolute inset-0">
          <div className="border-2 border-dashed" style={{ borderColor: leafColor }} />
        </div>

        {/* Leaf number */}
        <div className="absolute left-2 top-2">
          <div className="flex items-center justify-center w-6 h-6 rounded-full" style={{
            backgroundColor: leafColor,
          }}>
            <span className="text-xs font-medium text-white">{index + 1}</span>
          </div>
        </div>

        {/* Disease regions (if enabled and available) */}
        {showDiseaseRegions && leaf.disease_mask && (
          <div className="absolute inset-0" style={{ pointerEvents: "none" }}>
            {/* In a real implementation, we would render the disease mask as a semi-transparent overlay */}
            {/* For now, we'll show a simple indicator */}
            {leaf.diseased_area_ratio > 0.1 && (
              <div className="absolute inset-0" style={{
                backgroundColor: "hsl(var(--warning))",
                opacity: leaf.diseased_area_ratio * 0.3,
              }} />
            )}
          </div>
        )}

        {/* Grad-CAM visualization (if enabled and available) */}
        {showGradCAM && leaf.explainability_heatmap && (
          <div className="absolute inset-0" style={{ pointerEvents: "none" }}>
            {/* In a real implementation, we would render the heatmap as a colored overlay */}
            {/* For now, we'll show a simple indicator */}
            <div className="absolute inset-0" style={{
              backgroundColor: "hsl(var(--ai-accent))",
              opacity: 0.2,
            }} />
          </div>
        )}
      </div>
    );
  });

  return (
    <div className="relative w-full h-96">
      <img
        src={imageUrl}
        alt="Plant scan"
        className="w-full h-full object-cover rounded-xl"
        onLoad={handleImageLoad}
      />
      <div className="absolute inset-0 pointer-events-none">
        {leafElements}
      </div>
      <div className="absolute bottom-4 left-4 space-x-2">
        {/* Legend */}
        <div className="flex items-center gap-2 text-xs">
          <div className="w-3 h-3 rounded border border-dashed" style={{ borderColor: "hsl(var(--success))" }} />
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div className="w-3 h-3 rounded border border-dashed" style={{ borderColor: "hsl(var(--warning))" }} />
          <span>Warning</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div className="w-3 h-3 rounded border border-dashed" style={{ borderColor: "hsl(var(--destructive))" }} />
          <span>Issue</span>
        </div>
      </div>
    </div>
  );
}