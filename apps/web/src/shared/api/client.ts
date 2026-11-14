import { env } from "@/shared/config/env"

export class ApiError extends Error {
  readonly status: number
  readonly payload?: unknown

  constructor(status: number, message: string, payload?: unknown) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.payload = payload
  }
}

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown
}

export async function apiRequest<TResponse>(
  path: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const { body, headers, ...rest } = options
  const response = await fetch(`${env.apiBaseUrl}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => undefined)
    let message = response.statusText
    if (payload && typeof payload === "object") {
      if ("message" in payload && typeof payload.message === "string") {
        message = payload.message
      }
      if ("upstream_category" in payload) {
        if (payload.upstream_category === "http_response" &&
            "upstream_status" in payload && typeof payload.upstream_status === "number" &&
            Number.isInteger(payload.upstream_status) &&
            payload.upstream_status >= 100 && payload.upstream_status <= 599) {
          message += ` Keitaro returned HTTP ${payload.upstream_status}.`
        } else if (payload.upstream_category === "transport") {
          message += " No HTTP response was received from Keitaro."
        } else if (payload.upstream_category === "malformed_response") {
          message += " Keitaro returned an invalid response."
        }
      }
    }
    throw new ApiError(response.status, message, payload)
  }

  return (await response.json()) as TResponse
}
