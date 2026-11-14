import { ApiError } from "@/shared/api"

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload
    if (typeof payload === "object" && payload !== null) {
      if ("message" in payload && typeof payload.message === "string" && payload.message) {
        return payload.message
      }
      if ("code" in payload && payload.code === "KEITARO_UNAVAILABLE") {
        return "Keitaro недоступен. Проверьте подключение и попробуйте снова."
      }
    }
  }
  return "Не удалось выполнить запрос"
}
