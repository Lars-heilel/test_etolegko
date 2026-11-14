import re

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from app.domain.keitaro.exceptions import (
    CampaignNotFoundError,
    DomainError,
    OfferAlreadyExistsError,
    OfferNotFoundError,
)
from app.infrastructure.keitaro.errors import KeitaroResponseError, KeitaroUnavailableError
from app.main import create_app


async def test_missing_flow_returns_machine_code(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/campaigns/42/flows/999/offers/1")
    assert response.status_code == 404
    assert response.json() == {
        "code": "CAMPAIGN_NOT_FOUND",
        "message": "Flow 999 is not loaded for this campaign",
    }
    assert response.headers["x-request-id"]


@pytest.mark.parametrize("supplied", [None, "", "unsafe\r\nheader", "a" * 129, "a b", "é"])
async def test_request_id_is_generated_for_missing_or_unsafe_input(supplied: str | None) -> None:
    app = create_app()

    @app.get("/request-state")
    async def state(request: Request) -> dict[str, str]:
        return {"request_id": request.state.request_id}

    headers = [] if supplied is None else [(b"x-request-id", supplied.encode("latin-1"))]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/request-state", headers=headers)
        second = await client.get("/api/v1/health")
    request_id = response.headers["x-request-id"]
    assert re.fullmatch("[0-9a-f]{32}", request_id)
    assert response.json()["request_id"] == request_id
    assert second.headers["x-request-id"] != request_id


async def test_valid_request_id_is_echoed_and_exposed_to_browser(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "trace_123.test-ABC", "Origin": "http://localhost:5173"},
    )
    assert response.headers["x-request-id"] == "trace_123.test-ABC"
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (CampaignNotFoundError("Missing campaign"), 404, "CAMPAIGN_NOT_FOUND"),
        (OfferNotFoundError("Missing offer"), 404, "CAMPAIGN_NOT_FOUND"),
        (OfferAlreadyExistsError("Duplicate"), 409, "OFFER_ALREADY_EXISTS"),
        (DomainError("Invalid"), 422, "VALIDATION_ERROR"),
        (KeitaroResponseError(500, "secret upstream body"), 502, "KEITARO_UNAVAILABLE"),
        (KeitaroUnavailableError("secret URL and key"), 503, "KEITARO_UNAVAILABLE"),
    ],
)
async def test_error_mapping_is_sanitized(error: Exception, status: int, code: str) -> None:
    app: FastAPI = create_app()

    @app.get("/failure")
    async def failure() -> None:
        raise error

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/failure", headers={"X-Request-ID": "failure-123"})
    assert response.status_code == status
    assert response.json()["code"] == code
    assert "message" in response.json()
    assert "secret" not in response.text
    assert response.headers["x-request-id"] == "failure-123"


async def test_validation_uses_flat_envelope_without_raw_input(client: AsyncClient) -> None:
    response = await client.post("/api/v1/campaigns", json={"country_code": "private-secret"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["errors"]
    assert "private-secret" not in response.text
    assert response.headers["x-request-id"]


async def test_duplicate_request_ids_are_replaced(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/health", headers=[("X-Request-ID", "first"), ("X-Request-ID", "second")]
    )
    assert re.fullmatch("[0-9a-f]{32}", response.headers["x-request-id"])


async def test_preflight_has_request_id(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "X-Request-ID": "preflight-123",
        },
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "preflight-123"
