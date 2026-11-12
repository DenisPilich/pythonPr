import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError } from "./client";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("sends filters and auth headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({ items: [], total: 0, limit: 20, offset: 0 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const page = await api.jobs({ q: "python", technology: ["fastapi"], limit: 20 });

    expect(page.total).toBe(0);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/jobs?q=python&technology=fastapi&limit=20");
    const headers = (init as RequestInit).headers as Headers;
    expect(headers.get("X-API-Key")).toBeTruthy();
    expect(headers.get("X-Telegram-Id")).toBeTruthy();
  });

  it("maps problem responses to ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "Vacancy not found", code: "not_found" }, 404),
      ),
    );

    await expect(api.job("missing")).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      message: "Vacancy not found",
    });
  });

  it("returns null for a missing profile", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse({ detail: "Profile not found", code: "not_found" }, 404),
      ),
    );

    await expect(api.profile()).resolves.toBeNull();
  });

  it("exposes the status on ApiError instances", () => {
    const error = new ApiError(429, "Too many", "rate_limited");
    expect(error).toBeInstanceOf(Error);
    expect(error.status).toBe(429);
    expect(error.code).toBe("rate_limited");
  });
});
