import json
from collections.abc import Iterator

import httpx
import pytest
import respx
from httpx import AsyncClient

from app.infrastructure.config import get_settings

BASE = "https://tracker.example.com/admin_api/v1"


@pytest.fixture(autouse=True)
def tracker_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@respx.mock
async def test_create_source_returns_catalog_item(client: AsyncClient) -> None:
    upstream = respx.post(f"{BASE}/traffic_sources").respond(
        200, json={"id": 15, "name": "My source", "state": "active"}
    )
    response = await client.post("/api/v1/traffic-sources", json={"name": "  My source  "})
    assert response.status_code == 201
    assert response.json() == {"id": 15, "name": "My source"}
    assert json.loads(upstream.calls[0].request.content) == {"name": "My source"}
    assert upstream.call_count == 1


@pytest.mark.parametrize("payload", [{}, {"name": "   "}, {"name": None}])
@respx.mock
async def test_invalid_source_never_writes(client: AsyncClient, payload: dict) -> None:
    response = await client.post("/api/v1/traffic-sources", json=payload)
    assert response.status_code == 422
    assert not respx.calls


@pytest.mark.parametrize("failure", ["403", "timeout", "malformed"])
@respx.mock
async def test_source_failure_is_safe_and_not_retried(client: AsyncClient, failure: str) -> None:
    upstream = respx.post(f"{BASE}/traffic_sources")
    if failure == "403":
        upstream.respond(403, json={"error": "secret upstream details"})
    elif failure == "timeout":
        upstream.mock(side_effect=httpx.ReadTimeout("secret upstream details"))
    else:
        upstream.respond(200, json={"id": True, "name": "Source"})
    response = await client.post("/api/v1/traffic-sources", json={"name": "Source"})
    assert response.status_code == 502
    assert "secret" not in response.text
    assert upstream.call_count == 1
    if failure == "403":
        assert response.json()["upstream_status"] == 403
    else:
        assert "проверьте" in response.json()["message"].lower()
