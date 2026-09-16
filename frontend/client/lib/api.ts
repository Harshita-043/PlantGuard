import {
  PlantAnalysisResponse,
  LeafResult,
  PlantHealthSummary
} from '@/shared/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const analysisApi = {
  /**
   * Analyze a plant image for health assessment
   */
  analyzeImage: async (imageFile: File): Promise<PlantAnalysisResponse> => {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(`${API_BASE_URL}/api/v1/analyze/image`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to analyze image');
    }

    return response.json();
  },

  /**
   * Analyze a plant video frame for health assessment
   */
  analyzeVideo: async (videoFile: File): Promise<PlantAnalysisResponse> => {
    const formData = new FormData();
    formData.append('file', videoFile);

    const response = await fetch(`${API_BASE_URL}/api/v1/analyze/video`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to analyze video');
    }

    return response.json();
  },

  /**
   * Get analysis results by ID
   */
  getAnalysis: async (analysisId: string): Promise<PlantAnalysisResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze/${analysisId}`);

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Analysis not found');
      }
      throw new Error('Failed to fetch analysis');
    }

    return response.json();
  },

  /**
   * Health check for the analysis service
   */
  healthCheck: async (): Promise<{ status: string; service: string; ml_mode: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/v1/analyze/health`);
    if (!response.ok) {
      throw new Error('Health check failed');
    }
    return response.json();
  }
};

// Legacy API endpoints (keeping for compatibility)
export const legacyApi = {
  ping: async (): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/ping`);
    return response.json();
  },

  demo: async (): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/demo`);
    return response.json();
  }
};