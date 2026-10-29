import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, analysisApi } from "@/lib/api";

describe("analysis API errors", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("preserves the failed analysis reference and typed inference error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              analysis_id: "scan-123",
              code: "MODEL_UNAVAILABLE",
              stage: "sam",
              message: "The model runtime is unavailable.",
            },
          }),
          { status: 503, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await expect(
      analysisApi.getAnalysis("scan-123", "token"),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      analysisId: "scan-123",
      code: "MODEL_UNAVAILABLE",
      stage: "sam",
      message: "The model runtime is unavailable.",
    } satisfies Partial<ApiError>);
  });

  it("continues to handle plain string API details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "Upload rejected." }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(
      analysisApi.getAnalysis("scan-123", "token"),
    ).rejects.toMatchObject({
      name: "ApiError",
      status: 400,
      message: "Upload rejected.",
    });
  });
});

describe("analysis assets and deletion", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads owner-scoped asset links with the bearer token", async () => {
    const body = { analysis_id: "scan-1", assets: [] };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      analysisApi.getAnalysisAssets("scan-1", "owner-token"),
    ).resolves.toEqual(body);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/analysis/scan-1/assets");
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer owner-token",
    );
  });

  it("fetches local proxy assets with owner authentication", async () => {
    const blob = new Blob(["mask"], { type: "image/png" });
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(blob, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      analysisApi.getAssetBlob(
        "/api/v1/analysis/scan-1/asset?key=mask",
        "owner-token",
      ),
    ).resolves.toBeInstanceOf(Blob);
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer owner-token",
    );
  });

  it("fetches a presigned asset without sending the application bearer token", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(new Blob(["mask"]), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await analysisApi.getAssetBlob(
      "https://storage.example.test/signed?token=temporary",
      "owner-token",
    );
    expect(fetchMock.mock.calls[0][0]).toBe(
      "https://storage.example.test/signed?token=temporary",
    );
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it("deletes an analysis without trying to parse a 204 body", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      analysisApi.deleteAnalysis("scan-1", "owner-token"),
    ).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0][1].method).toBe("DELETE");
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe(
      "Bearer owner-token",
    );
  });
});
