import httpx
import pytest
import respx

from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.errors import KeitaroResponseError, KeitaroUnavailableError

URL = "https://tracker.example.com/admin_api/v1/campaigns"


@respx.mock
async def test_client_sends_api_key_and_closes() -> None:
    route = respx.get(URL).respond(200, json=[{"id": 1}])
    async with KeitaroClient("https://tracker.example.com/", "test-key") as client:
        assert await client.get("/campaigns") == [{"id": 1}]
    assert route.calls[0].request.headers["Api-Key"] == "test-key"
    assert client._client.is_closed


@pytest.mark.parametrize("method", ["GET", "PUT"])
@pytest.mark.parametrize("failure", [httpx.Response(503), httpx.ReadTimeout("timeout")])
@respx.mock
async def test_idempotent_requests_retry(method: str, failure: object) -> None:
    route = respx.route(method=method, url=URL).mock(
        side_effect=[failure, httpx.Response(200, json={"ok": True})]
    )
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        result = (
            await client.get("/campaigns")
            if method == "GET"
            else await client.put("/campaigns", json={})
        )
    assert result == {"ok": True}
    assert route.call_count == 2


@pytest.mark.parametrize("failure", [httpx.Response(500), httpx.ReadTimeout("timeout")])
@respx.mock
async def test_post_never_retries(failure: object) -> None:
    route = respx.post(URL).mock(side_effect=[failure])
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        with pytest.raises(KeitaroUnavailableError):
            await client.post("/campaigns", json={"name": "One"})
    assert route.call_count == 1


@pytest.mark.parametrize("failure", [httpx.Response(502), httpx.ConnectError("offline")])
@respx.mock
async def test_get_exhausts_three_attempts(failure: object) -> None:
    route = respx.get(URL).mock(side_effect=[failure, failure, failure])
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        with pytest.raises(KeitaroUnavailableError):
            await client.get("/campaigns")
    assert route.call_count == 3


@pytest.mark.parametrize(
    "response, message",
    [
        (httpx.Response(400, json={"message": "Bad request"}), "Bad request"),
        (httpx.Response(401, json={"error": "Unauthorized"}), "Unauthorized"),
        (httpx.Response(429, json=["Rate limited"]), "Rate limited"),
        (httpx.Response(404, text="Not found"), "Not found"),
    ],
)
@respx.mock
async def test_response_errors_are_not_retried(response: httpx.Response, message: str) -> None:
    route = respx.get(URL).mock(return_value=response)
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        with pytest.raises(KeitaroResponseError, match=message) as error:
            await client.get("/campaigns")
    assert error.value.status_code == response.status_code
    assert route.call_count == 1


@respx.mock
async def test_invalid_success_json_is_a_typed_error_without_retry() -> None:
    route = respx.post(URL).respond(200, text="not JSON")
    async with KeitaroClient("https://tracker.example.com", "test-key") as client:
        with pytest.raises(KeitaroResponseError):
            await client.post("/campaigns", json={})
    assert route.call_count == 1


@pytest.mark.parametrize("base_url, api_key", [("", "key"), ("https://example.com", "")])
def test_missing_configuration(base_url: str, api_key: str) -> None:
    with pytest.raises(KeitaroUnavailableError):
        KeitaroClient(base_url, api_key)
