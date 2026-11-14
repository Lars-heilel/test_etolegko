class DomainError(Exception):
    code = "VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCountryCodeError(DomainError):
    pass


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
