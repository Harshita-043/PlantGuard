import { ScanResponse, ScanSummary, ScanDetail, HealthReportResponse } from '@/shared/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const scanApi = {
  /**
   * Upload a plant image and initiate health analysis
   */
  uploadScan: async (imageFile: File): Promise<ScanResponse> => {
    const formData = new FormData();
    formData.append('file', imageFile);

    const response = await fetch(`${API_BASE_URL}/api/scan`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to process scan');
    }

    return response.json();
  },

  /**
   * Get paginated list of user's scans
   */
  getScanHistory: async (skip = 0, limit = 10): Promise<ScanSummary[]> => {
    const response = await fetch(`${API_BASE_URL}/api/scans?skip=${skip}&limit=${limit}`);

    if (!response.ok) {
      throw new Error('Failed to fetch scan history');
    }

    return response.json();
  },

  /**
   * Get detailed results for a specific scan
   */
  getScanDetails: async (scanId: string): Promise<ScanDetail> => {
    const response = await fetch(`${API_BASE_URL}/api/scans/${scanId}`);

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Scan not found');
      }
      throw new Error('Failed to fetch scan details');
    }

    return response.json();
  },

  /**
   * Get formatted health report for a specific scan
   */
  getScanReport: async (scanId: string): Promise<HealthReportResponse> => {
    const response = await fetch(`${API_BASE_URL}/api/scans/${scanId}/report`);

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Scan not found');
      }
      throw new Error('Failed to fetch scan report');
    }

    return response.json();
  }
};

// Health check endpoints
export const healthApi = {
  ping: async (): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/ping`);
    return response.json();
  },

  demo: async (): Promise<{ message: string }> => {
    const response = await fetch(`${API_BASE_URL}/api/demo`);
    return response.json();
  }
};