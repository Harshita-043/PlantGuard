/**
 * Shared code between client and server
 * Useful to share types between client and server
 * and/or small pure JS functions that can be used on both client and server
 */

/**
 * Example response type for /api/demo
 */
export interface DemoResponse {
  message: string;
}

/**
 * Plant health analysis types (v1 API)
 */
export interface LeafResult {
  leaf_index: number;
  bounding_box: [number, number, number, number]; // [x_min, y_min, width, height] normalized 0-1
  disease_class: string;
  classification_confidence: number; // 0-1
  all_probabilities?: Record<string, number>;
  disease_mask?: boolean[][]; // 2D boolean array
  diseased_area_ratio: number; // 0-1
  disease_bounding_box: [number, number, number, number]; // [x_min, y_min, width, height] normalized
  severity_score: number; // 0-1
  severity_level: "low" | "medium" | "high";
  affected_percentage: number; // 0-100
  leaf_confidence?: number; // 0-1
  explainability_heatmap?: number[][]; // 2D float array (0-1)
}

export interface PlantHealthSummary {
  overall_health_score: number; // 0-100
  health_status: "excellent" | "good" | "fair" | "poor" | "critical";
  healthy_leaf_count: number;
  total_leaf_count: number;
  disease_summary: Record<string, number>;
  risk_assessment: string; // e.g., 'low', 'medium', 'high'
  recommendations: string[];
}

export interface PlantAnalysisResponse {
  analysis_id: string;
  timestamp: string; // ISO date string
  status: string; // 'completed', 'failed', 'processing'
  leaf_results: LeafResult[];
  plant_health_summary: PlantHealthSummary;
  processing_time_ms?: number;
  ml_mode: string; // 'mock' or 'real'
}

/** Persisted image lifecycle metadata; it contains no inferred plant results. */
export interface AnalysisLifecycleResponse {
  analysis_id: string;
  plant_id: string | null;
  status: "pending" | "completed" | "failed";
  created_at: string;
  image_content_type: string;
  image_size_bytes: number;
  result_available: boolean;
  /** Present only when inference completed successfully. */
  result: FullScanResult | null;
  failure: {
    code: string;
    stage: string;
    message: string;
    occurred_at: string;
  } | null;
}

export interface AnalysisAssetLink {
  storage_key: string;
  kind: "original" | "artifact";
  download_url: string;
  expires_in_seconds: number | null;
}

export interface AnalysisAssetsResponse {
  analysis_id: string;
  assets: AnalysisAssetLink[];
}

export interface MaskAsset {
  storage_key: string;
  content_type: string;
  width: number;
  height: number;
  byte_size: number | null;
  download_url: string | null;
}
export interface PipelineWarning {
  code: string;
  message: string;
  component: string;
  severity: "info" | "warning" | "critical";
}

export interface FullScanResult {
  schema_version: string;
  analysis_id: string;
  timestamp: string;
  status: string;
  hardware_device: string;
  processing_time_ms: number;
  model_versions: Record<string, string>;
  stage_timings_ms: Record<string, number>;
  model_load_timings_ms: Record<string, number>;
  candidate_counts?: {
    generated: number;
    valid: number;
    deduplicated: number;
    leaf_filter_accepted: number;
    disease_analysis_eligible: number;
  };
  leaves: SingleLeafAnalysis[];
  plant_summary: PlantHealthSummaryV2;
  warnings: PipelineWarning[];
  partial_failures: Array<{
    component: string;
    error_type: string;
    message: string;
    fallback_applied: boolean;
  }>;
}

export interface PlantHealthSummaryV2 {
  overall_health_score: number | null;
  health_status:
    "healthy" | "mildly_diseased" | "severely_diseased" | "unknown";
  total_leaves_detected: number;
  valid_leaves_analyzed: number;
  healthy_leaves_count: number;
  diseased_leaves_count: number;
  primary_diagnosis: string | null;
  disease_breakdown: Record<string, number>;
  average_severity_percentage: number | null;
  recommendations: string[];
}

export interface SingleLeafAnalysis {
  leaf_id: number;
  bounding_box: [number, number, number, number];
  is_leaf: boolean;
  leaf_filter_confidence: number;
  candidate_score: number;
  candidate_source: string;
  leaf_mask_asset: MaskAsset | null;
  leaf_crop_asset: MaskAsset | null;
  lesion_overlay_asset: MaskAsset | null;
  attention_overlay_asset: MaskAsset | null;
  classification: {
    primary_class: string;
    confidence: number;
    is_healthy: boolean;
    crop_type: string | null;
    disease_name: string | null;
    top_k_probabilities: Record<string, number>;
  } | null;
  ood: {
    score: number;
    threshold: number;
    is_ood: boolean;
    method: string;
    status:
      | "ood_detected"
      | "ood_not_detected"
      | "ood_unavailable"
      | "ood_unvalidated";
    calibration_status: string;
  } | null;
  segmentation: {
    has_lesions: boolean;
    diseased_pixels: number;
    total_leaf_pixels: number;
    diseased_ratio: number;
    disease_bounding_box: number[] | null;
    mask_asset: MaskAsset | null;
  } | null;
  severity: {
    status: string;
    method: string;
    score: number | null;
    level: "healthy" | "low" | "medium" | "high" | null;
    affected_percentage: number | null;
    diseased_leaf_pixels: number | null;
    valid_leaf_pixels: number | null;
    thresholds_validated: boolean;
    assessment: string;
  } | null;
  explainability: {
    status: string;
    method: string;
    description: string | null;
    heatmap_asset: MaskAsset | null;
  } | null;
  prediction_uncertainty: {
    score: number;
    threshold: number;
    is_high_uncertainty: boolean;
    classification_confidence: number;
    method: string;
    calibration_status: string;
  } | null;
  warnings: PipelineWarning[];
}

/** Public account fields returned by the FastAPI authentication endpoints. */
export interface AuthUserResponse {
  id: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface HealthTrendPoint {
  analysis_id: string;
  timestamp: string;
  health_score: number;
  health_status: string;
  severity_percentage: number | null;
}

export interface DashboardMetricsResponse {
  total_analyses: number;
  healthy_analyses: number;
  diseased_analyses: number;
  inconclusive_analyses: number;
  failed_analyses: number;
  total_plants: number;
  average_health_score: number | null;
  disease_distribution: Record<string, number>;
  recent_scans: AnalysisLifecycleResponse[];
  health_trend: HealthTrendPoint[];
}

export interface PlantPayload {
  name: string;
  species: string | null;
  location: string | null;
  notes: string | null;
}

export interface PlantResponse extends PlantPayload {
  id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  total_scans: number;
  health_status: string | null;
  latest_analysis: AnalysisLifecycleResponse | null;
}

export interface PlantDetailResponse extends PlantResponse {
  recent_scans: AnalysisLifecycleResponse[];
  health_trend: HealthTrendPoint[];
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}
