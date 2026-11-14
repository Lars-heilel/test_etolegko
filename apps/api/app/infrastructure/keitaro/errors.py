from app.domain.keitaro.exceptions import GatewayError


class KeitaroError(GatewayError):
    pass


class KeitaroUnavailableError(KeitaroError):
    pass


class KeitaroResponseError(KeitaroError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
