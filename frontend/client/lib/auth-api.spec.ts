import { afterEach, describe, expect, it, vi } from "vitest";

import { authApi } from "./auth-api";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

describe("auth API client", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("registers and logs in against the FastAPI auth endpoints", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse(
          {
            id: "u1",
            email: "plant@example.com",
            created_at: "now",
            updated_at: "now",
          },
          201,
        ),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "jwt",
          token_type: "bearer",
          expires_in: 1800,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await authApi.register({
      email: "plant@example.com",
      password: "a-strong-password",
    });
    await authApi.login({
      email: "plant@example.com",
      password: "a-strong-password",
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/auth/register",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/auth/login",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        email: "plant@example.com",
        password: "a-strong-password",
      }),
    );
  });

  it("retrieves the current user with a bearer token", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse({
          id: "u1",
          email: "plant@example.com",
          created_at: "now",
          updated_at: "now",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    await authApi.currentUser("jwt-value");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/me",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer jwt-value" }),
      }),
    );
  });

  it("returns safe HTTP status information for rejected credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ detail: "Invalid email or password" }, 401),
        ),
    );

    await expect(
      authApi.login({ email: "plant@example.com", password: "wrong-password" }),
    ).rejects.toMatchObject({
      name: "AuthApiError",
      status: 401,
      message: "Invalid email or password",
    });
  });
});
