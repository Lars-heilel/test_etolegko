from typing import Literal

GatewayFailureCategory = Literal[
    "unknown", "transport", "http_response", "malformed_response", "configuration"
]


class DomainError(Exception):
    code = "VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCountryCodeError(DomainError):
    pass


class GatewayError(Exception):
    """An external gateway operation failed; its result may be unknown."""

    def __init__(
        self,
        message: str,
        *,
        upstream_status: int | None = None,
        upstream_category: GatewayFailureCategory = "unknown",
    ) -> None:
        super().__init__(message)
        self.upstream_status = upstream_status
        self.upstream_category = upstream_category


class CampaignCreationError(DomainError):
    code = "KEITARO_UNAVAILABLE"

    def __init__(
        self,
        campaign_id: int | None,
        failed_step: str,
        confirmed_flows: int,
        *,
        upstream_status: int | None = None,
        upstream_category: GatewayFailureCategory = "unknown",
    ) -> None:
        self.upstream_status = upstream_status
        self.upstream_category = upstream_category
        self.campaign_id = campaign_id
        self.failed_step = failed_step
        self.confirmed_flows = confirmed_flows
        message = (
            "Campaign creation could not be confirmed. Check Keitaro before creating again."
            if campaign_id is None
            else f"Campaign {campaign_id} was created, but setup could not be completed. "
            "Check its flows in Keitaro before creating again."
        )
        super().__init__(message)


class TrafficSourceCreationError(DomainError):
    code = "KEITARO_UNAVAILABLE"

    def __init__(self, error: GatewayError) -> None:
        self.upstream_status = error.upstream_status
        self.upstream_category = error.upstream_category
        message = (
            "Выданный API-ключ не имеет прав на создание источника в Keitaro."
            if error.upstream_status == 403
            else "Создание источника не подтверждено. Обновите каталоги и проверьте "
            "источники в Keitaro перед повторной попыткой."
        )
        super().__init__(message)


class CampaignNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class CampaignOffersSaveError(DomainError):
    code = "KEITARO_UNAVAILABLE"

    def __init__(self, failed_stream_id: int, confirmed_stream_ids: list[int]) -> None:
        self.failed_stream_id = failed_stream_id
        self.confirmed_stream_ids = list(confirmed_stream_ids)
        super().__init__(
            "Offer save could not be completed. Confirmed streams remain saved; "
            "the failed stream's result may be unknown. Check Keitaro before retrying."
        )


class FlowNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferAlreadyExistsError(DomainError):
    code = "OFFER_ALREADY_EXISTS"


class ShareTotalError(DomainError):
    pass
