import type { AnalysisLifecycleResponse } from "@shared/api";

export type { AnalysisLifecycleResponse } from "@shared/api";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function readError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body && typeof body.detail === "string") {
      message = body.detail;
    }
  } catch {
    // Use the safe status-based message for non-JSON errors.
  }
  return new ApiError(message, response.status);
}

async function authenticatedRequest<T>(path: string, accessToken: string, init: RequestInit = {}): Promise<T> {
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

export const analysisApi = {
  analyzeImage(imageFile: File, accessToken: string): Promise<AnalysisLifecycleResponse> {
    const formData = new FormData();
    formData.append("file", imageFile);
    return authenticatedRequest<AnalysisLifecycleResponse>("/api/v1/analyze/image", accessToken, {
      method: "POST",
      body: formData,
    });
  },

  getAnalysis(analysisId: string, accessToken: string): Promise<AnalysisLifecycleResponse> {
    return authenticatedRequest<AnalysisLifecycleResponse>(
      `/api/v1/analysis/${encodeURIComponent(analysisId)}`,
      accessToken,
    );
  },

  getAnalyses(accessToken: string, skip = 0, limit = 10): Promise<AnalysisLifecycleResponse[]> {
    const query = new URLSearchParams({ skip: String(skip), limit: String(limit) });
    return authenticatedRequest<AnalysisLifecycleResponse[]>(`/api/v1/analyses?${query}`, accessToken);
  },
};
