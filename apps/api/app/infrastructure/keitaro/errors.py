from app.domain.keitaro.exceptions import GatewayError


class KeitaroError(GatewayError):
    pass


class KeitaroUnavailableError(KeitaroError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(
            message,
            upstream_status=status_code,
            upstream_category="http_response" if status_code is not None else "transport",
        )


class KeitaroResponseError(KeitaroError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(
            message,
            upstream_status=status_code,
            upstream_category="http_response" if status_code >= 300 else "malformed_response",
        )
        self.status_code = status_code
        self.message = message
