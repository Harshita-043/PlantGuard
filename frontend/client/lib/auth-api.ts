import type {
  AuthUserResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
} from "@shared/api";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

export class AuthApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

async function readError(response: Response): Promise<AuthApiError> {
  let message = `Authentication request failed (${response.status})`;
  try {
    const body: unknown = await response.json();
    if (typeof body === "object" && body !== null && "detail" in body) {
      const detail = body.detail;
      if (typeof detail === "string") message = detail;
      else if (Array.isArray(detail))
        message = "Please check the submitted information.";
    }
  } catch {
    // Keep a safe status-based message if the server did not return JSON.
  }
  return new AuthApiError(message, response.status);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) throw await readError(response);
  return (await response.json()) as T;
}

export const authApi = {
  register(requestBody: RegisterRequest): Promise<AuthUserResponse> {
    return request<AuthUserResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  login(requestBody: LoginRequest): Promise<TokenResponse> {
    return request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(requestBody),
    });
  },

  currentUser(accessToken: string): Promise<AuthUserResponse> {
    return request<AuthUserResponse>("/api/v1/auth/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
  },
};
