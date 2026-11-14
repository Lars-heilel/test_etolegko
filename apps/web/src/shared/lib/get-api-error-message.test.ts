import { describe, expect, it } from "vitest"

import { ApiError } from "@/shared/api"
import { getApiErrorMessage } from "./get-api-error-message"

describe("getApiErrorMessage", () => {
  it("uses the backend message", () => {
    expect(getApiErrorMessage(new ApiError(409, "Conflict", {
      code: "OFFER_ALREADY_EXISTS",
      message: "Offer 2 already exists in the flow",
    }))).toBe("Offer 2 already exists in the flow")
  })

  it("preserves partial failure details instead of replacing them with connectivity advice", () => {
    const message = "Campaign 42 was created, but stream creation failed"
    expect(getApiErrorMessage(new ApiError(502, "Bad Gateway", {
      code: "KEITARO_UNAVAILABLE", message,
    }))).toBe(message)
  })

  it("provides connectivity advice when only the unavailable code is present", () => {
    expect(getApiErrorMessage(new ApiError(502, "Bad Gateway", {
      code: "KEITARO_UNAVAILABLE",
    }))).toBe("Keitaro недоступен. Проверьте подключение и попробуйте снова.")
  })

  it.each([new Error("boom"), null, undefined, "boom"])("falls back for unknown errors: %s", (error) => {
    expect(getApiErrorMessage(error)).toBe("Не удалось выполнить запрос")
  })

  it.each([undefined, null, {}, { message: 42 }, { message: "" }, "error"])("handles malformed API payloads: %s", (payload) => {
    expect(getApiErrorMessage(new ApiError(500, "Error", payload))).toBe("Не удалось выполнить запрос")
  })
})
