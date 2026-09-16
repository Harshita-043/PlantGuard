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
  severity_level: 'low' | 'medium' | 'high';
  affected_percentage: number; // 0-100
  leaf_confidence?: number; // 0-1
  explainability_heatmap?: number[][]; // 2D float array (0-1)
}

export interface PlantHealthSummary {
  overall_health_score: number; // 0-100
  health_status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
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

export interface CareRecommendation {
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  category: string; // e.g., 'watering', 'lighting', 'treatment'
}

/**
 * Legacy scan types (kept for backward compatibility)
 */
export interface ScanResponse {
  scan_id: string;
  message: string;
  status: string;
}

export interface ScanSummary {
  id: string;
  plant_name?: string;
  date: string; // ISO date string
  status: string;
  overall_health_score?: number;
}

export interface ScanDetail {
  id: string;
  plant_name?: string;
  date: string; // ISO date string
  status: string;
  image_url?: string;
  leaf_results: LeafResult[];
  health_report: PlantHealthSummary;
}

export interface HealthReportResponse {
  scan_id: string;
  overall_health_score: number; // 0-100
  health_status: string; // excellent, good, fair, poor, critical
  recommendations: string[];
}
