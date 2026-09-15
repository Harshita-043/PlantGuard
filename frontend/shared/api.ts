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
 * Plant health analysis types
 */
export interface LeafResult {
  leaf_index: number;
  bounding_box: [number, number, number, number]; // [x, y, width, height] normalized 0-1
  disease_class: string;
  classification_confidence: number; // 0-1
  all_probabilities?: Record<string, number>;
  diseased_area_ratio: number; // 0-1
  disease_bounding_box: [number, number, number, number]; // [x, y, width, height] normalized
  severity_score: number; // 0-1
  severity_level: 'low' | 'medium' | 'high';
  affected_percentage: number; // 0-100
  leaf_confidence?: number; // 0-1
}

export interface HealthReport {
  overall_health_score: number; // 0-100
  risk_assessment: 'low' | 'medium' | 'high';
  healthy_leaf_count: number;
  total_leaf_count: number;
  disease_summary: Record<string, number>;
  recommendations: string[];
}

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
  health_report: HealthReport;
}

export interface HealthReportResponse {
  scan_id: string;
  overall_health_score: number; // 0-100
  health_status: string; // excellent, good, fair, poor, critical
  recommendations: string[];
}
