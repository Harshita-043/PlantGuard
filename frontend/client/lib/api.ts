import type {
  AnalysisAssetLink,
  AnalysisAssetsResponse,
  AnalysisLifecycleResponse,
  DashboardMetricsResponse,
  PlantDetailResponse,
  PlantPayload,
  PlantResponse,
} from "@shared/api";

export type {
  AnalysisAssetLink,
  AnalysisAssetsResponse,
  AnalysisLifecycleResponse,
  DashboardMetricsResponse,
  PlantDetailResponse,
  PlantPayload,
  PlantResponse,
} from "@shared/api";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
    readonly stage?: string,
    readonly analysisId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  let code: string | undefined;
  let stage: string | undefined;
  let analysisId: string | undefined;
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") message = detail;
      else if (typeof detail === "object" && detail !== null) {
        if ("message" in detail && typeof detail.message === "string")
          message = detail.message;
        if ("code" in detail && typeof detail.code === "string")
          code = detail.code;
        if ("stage" in detail && typeof detail.stage === "string")
          stage = detail.stage;
        if ("analysis_id" in detail && typeof detail.analysis_id === "string")
          analysisId = detail.analysis_id;
      }
    }
  } catch {
    // Use the safe status-based message for non-JSON errors.
  }
  return new ApiError(message, response.status, code, stage, analysisId);
}

async function authenticatedRequest<T>(
  path: string,
  accessToken: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${accessToken}`,
      ...init.headers,
    },
  });
  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

async function authenticatedBlob(
  path: string,
  accessToken: string,
): Promise<Blob> {
  const isSignedUrl = path.startsWith("https://");
  const response = await fetch(isSignedUrl ? path : `${API_BASE_URL}${path}`, {
    headers: isSignedUrl
      ? { Accept: "image/png,image/jpeg,image/webp" }
      : {
          Accept: "image/png,image/jpeg,image/webp",
          Authorization: `Bearer ${accessToken}`,
        },
  });
  if (!response.ok) throw await readError(response);
  return response.blob();
}
export const analysisApi = {
  analyzeImage(
    imageFile: File,
    accessToken: string,
    plantId?: string,
  ): Promise<AnalysisLifecycleResponse> {
    const formData = new FormData();
    formData.append("file", imageFile);
    const query = plantId ? `?plant_id=${encodeURIComponent(plantId)}` : "";
    return authenticatedRequest<AnalysisLifecycleResponse>(
      `/api/v1/analyze/image${query}`,
      accessToken,
      {
        method: "POST",
        body: formData,
      },
    );
  },

  getAnalysis(
    analysisId: string,
    accessToken: string,
  ): Promise<AnalysisLifecycleResponse> {
    return authenticatedRequest<AnalysisLifecycleResponse>(
      `/api/v1/analysis/${encodeURIComponent(analysisId)}`,
      accessToken,
    );
  },

  getAnalysisAssets(
    analysisId: string,
    accessToken: string,
  ): Promise<AnalysisAssetsResponse> {
    return authenticatedRequest<AnalysisAssetsResponse>(
      `/api/v1/analysis/${encodeURIComponent(analysisId)}/assets`,
      accessToken,
    );
  },

  getAssetBlob(downloadUrl: string, accessToken: string): Promise<Blob> {
    return authenticatedBlob(downloadUrl, accessToken);
  },

  async deleteAnalysis(analysisId: string, accessToken: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/analysis/${encodeURIComponent(analysisId)}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` },
      },
    );
    if (!response.ok) throw await readError(response);
  },

  getAnalyses(
    accessToken: string,
    skip = 0,
    limit = 10,
  ): Promise<AnalysisLifecycleResponse[]> {
    const query = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
    });
    return authenticatedRequest<AnalysisLifecycleResponse[]>(
      `/api/v1/analyses?${query}`,
      accessToken,
    );
  },
};

export const dashboardApi = {
  getMetrics(accessToken: string): Promise<DashboardMetricsResponse> {
    return authenticatedRequest<DashboardMetricsResponse>(
      "/api/v1/dashboard/metrics",
      accessToken,
    );
  },
};

export const plantsApi = {
  getPlants(accessToken: string): Promise<PlantResponse[]> {
    return authenticatedRequest<PlantResponse[]>("/api/v1/plants", accessToken);
  },

  getPlant(
    plantId: string,
    accessToken: string,
  ): Promise<PlantDetailResponse> {
    return authenticatedRequest<PlantDetailResponse>(
      `/api/v1/plants/${encodeURIComponent(plantId)}`,
      accessToken,
    );
  },

  createPlant(
    payload: PlantPayload,
    accessToken: string,
  ): Promise<PlantResponse> {
    return authenticatedRequest<PlantResponse>("/api/v1/plants", accessToken, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  },

  updatePlant(
    plantId: string,
    payload: PlantPayload,
    accessToken: string,
  ): Promise<PlantResponse> {
    return authenticatedRequest<PlantResponse>(
      `/api/v1/plants/${encodeURIComponent(plantId)}`,
      accessToken,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
  },

  async deletePlant(plantId: string, accessToken: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/plants/${encodeURIComponent(plantId)}`,
      {
        method: "DELETE",
        headers: { Authorization: `Bearer ${accessToken}` },
      },
    );
    if (!response.ok) throw await readError(response);
  },

  associateScan(
    plantId: string,
    analysisId: string,
    accessToken: string,
  ): Promise<AnalysisLifecycleResponse> {
    return authenticatedRequest<AnalysisLifecycleResponse>(
      `/api/v1/plants/${encodeURIComponent(plantId)}/scans/${encodeURIComponent(analysisId)}`,
      accessToken,
      { method: "POST" },
    );
  },

  disassociateScan(
    plantId: string,
    analysisId: string,
    accessToken: string,
  ): Promise<AnalysisLifecycleResponse> {
    return authenticatedRequest<AnalysisLifecycleResponse>(
      `/api/v1/plants/${encodeURIComponent(plantId)}/scans/${encodeURIComponent(analysisId)}`,
      accessToken,
      { method: "DELETE" },
    );
  },
};
