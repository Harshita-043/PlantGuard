import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, Loader, ScanLine } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/auth/AuthContext";
import { ApiError, analysisApi, plantsApi } from "@/lib/api";
import type { PlantResponse } from "@shared/api";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const SUPPORTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

export default function ScanPage() {
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plants, setPlants] = useState<PlantResponse[]>([]);
  const [selectedPlantId, setSelectedPlantId] = useState("");
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  useEffect(() => {
    setSelectedPlantId(searchParams.get("plant_id") ?? "");
  }, [searchParams]);

  useEffect(() => {
    let active = true;
    if (!accessToken) return;
    plantsApi
      .getPlants(accessToken)
      .then((records) => {
        if (active) setPlants(records);
      })
      .catch((caught: unknown) => {
        if (caught instanceof ApiError && caught.status === 401) {
          logout();
          navigate("/login", { replace: true });
        } else if (active) {
          setError(caught instanceof Error ? caught.message : "Plant list could not be loaded.");
        }
      });
    return () => {
      active = false;
    };
  }, [accessToken, logout, navigate]);

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setError(null);
    if (!file) {
      setImageFile(null);
      return;
    }
    if (!SUPPORTED_TYPES.has(file.type)) {
      setError("Choose a JPEG, PNG, or WebP image.");
      setImageFile(null);
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError("The image must be 10 MB or smaller.");
      setImageFile(null);
      return;
    }
    setImageFile(file);
  };

  const handleUpload = useCallback(async () => {
    if (!imageFile || !accessToken) return;
    setIsUploading(true);
    setError(null);
    try {
      const analysis = await analysisApi.analyzeImage(
        imageFile,
        accessToken,
        selectedPlantId || undefined,
      );
      navigate(`/scan/results/${analysis.analysis_id}`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        logout();
        navigate("/login", { replace: true });
        return;
      }
      if (caught instanceof ApiError && caught.analysisId) {
        navigate(`/scan/results/${encodeURIComponent(caught.analysisId)}`);
        return;
      }
      setError(
        caught instanceof Error
          ? caught.message
          : "The image could not be uploaded.",
      );
    } finally {
      setIsUploading(false);
    }
  }, [accessToken, imageFile, logout, navigate, selectedPlantId]);

  return (
    <section className="mx-auto max-w-2xl space-y-6 rounded-2xl border border-border bg-card p-6 sm:p-8">
      <div className="text-center">
        <span className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl bg-primary/10 text-primary">
          <ScanLine size={24} />
        </span>
        <h2 className="text-2xl font-semibold tracking-[-0.04em]">
          Save a plant image
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The image is saved to your account and analyzed when the configured
          model runtime and artifacts are available.
        </p>
      </div>

      <div className="space-y-3">
        <label className="grid gap-2 text-sm" htmlFor="plant-association">
          Associate with a plant (optional)
          <select
            id="plant-association"
            value={selectedPlantId}
            onChange={(event) => setSelectedPlantId(event.target.value)}
            disabled={isUploading}
            className="rounded-lg border border-border bg-background p-3"
          >
            <option value="">No plant association</option>
            {plants.map((plant) => (
              <option key={plant.id} value={plant.id}>{plant.name}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="space-y-3">
        <Label htmlFor="image-upload">Plant image</Label>
        <input
          id="image-upload"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleImageChange}
          disabled={isUploading}
          className="block w-full rounded-lg border border-border p-3 text-sm"
        />
        <p className="text-xs text-muted-foreground">
          JPEG, PNG, or WebP. Maximum size 10 MB.
        </p>
        {imageFile && (
          <p className="text-sm text-muted-foreground">
            Selected: {imageFile.name}
          </p>
        )}
      </div>

      {error && (
        <div
          className="flex items-start gap-2 rounded-xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <Button
        onClick={() => void handleUpload()}
        disabled={!imageFile || isUploading || !accessToken}
        className="w-full"
      >
        {isUploading ? (
          <>
            <Loader size={16} className="mr-2 animate-spin" />
            Analyzing image…
          </>
        ) : (
          "Analyze plant image"
        )}
      </Button>
    </section>
  );
}
