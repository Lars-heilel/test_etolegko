class DomainError(Exception):
    code = "VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCountryCodeError(DomainError):
    pass


class GatewayError(Exception):
    """An external gateway operation failed; its result may be unknown."""


class CampaignCreationError(DomainError):
    code = "KEITARO_UNAVAILABLE"

    def __init__(self, campaign_id: int | None, failed_step: str, confirmed_flows: int) -> None:
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


class CampaignNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class FlowNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferAlreadyExistsError(DomainError):
    code = "OFFER_ALREADY_EXISTS"


class ShareTotalError(DomainError):
    pass
