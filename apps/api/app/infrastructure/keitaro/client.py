import asyncio
from types import TracebackType
from typing import Any, Self

import httpx

from app.infrastructure.keitaro.errors import KeitaroResponseError, KeitaroUnavailableError


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0) -> None:
        if not base_url or not api_key:
            raise KeitaroUnavailableError("Keitaro URL and API key are not configured")
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Api-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        # A failed POST may already have created a resource on the tracker.
        attempts = 3 if method in {"GET", "PUT"} else 1
        message = "Keitaro is unavailable"
        for attempt in range(attempts):
            try:
                response = await self._client.request(method, f"/admin_api/v1{path}", **kwargs)
            except httpx.TransportError:
                # Transport exceptions can contain URLs; keep credentials out of errors.
                message = "Could not connect to Keitaro"
            else:
                if response.status_code >= 500:
                    message = f"Keitaro returned {response.status_code}"
                elif response.status_code >= 400:
                    error_message = response.text
                    try:
                        payload = response.json()
                    except ValueError:
                        pass
                    else:
                        if isinstance(payload, dict):
                            error_message = (
                                payload.get("message") or payload.get("error") or error_message
                            )
                    raise KeitaroResponseError(response.status_code, str(error_message))
                else:
                    try:
                        return response.json()
                    except ValueError:
                        raise KeitaroResponseError(
                            response.status_code, "Keitaro returned invalid JSON"
                        ) from None
            if attempt + 1 < attempts:
                await asyncio.sleep(0.2 * (2**attempt))
        raise KeitaroUnavailableError(message)

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: Any) -> Any:
        return await self._request("PUT", path, json=json)
