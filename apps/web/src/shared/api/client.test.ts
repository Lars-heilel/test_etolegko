import { afterEach, expect, it, vi } from "vitest"

import { apiRequest } from "./client"

afterEach(() => vi.unstubAllGlobals())

it("shows the server message and safe upstream status without raw body fields", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({
    message: "Campaign creation could not be confirmed.",
    upstream_status: 403,
    upstream_category: "http_response",
    raw: "secret-token",
  }), { status: 502, statusText: "Bad Gateway" })))
  await expect(apiRequest("/campaigns")).rejects.toThrow(
    "Campaign creation could not be confirmed. Keitaro returned HTTP 403.",
  )
})

it("falls back to HTTP status text for an invalid error payload", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("invalid", {
    status: 502, statusText: "Bad Gateway",
  })))
  await expect(apiRequest("/campaigns")).rejects.toThrow("Bad Gateway")
})
