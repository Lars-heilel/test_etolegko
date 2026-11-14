import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.keitaro.exceptions import (
    CampaignCreationError,
    CampaignNotFoundError,
    CampaignOffersSaveError,
    DomainError,
    FlowNotFoundError,
    OfferAlreadyExistsError,
    OfferNotFoundError,
    TrafficSourceCreationError,
)
from app.infrastructure.keitaro.errors import KeitaroError, KeitaroUnavailableError

logger = logging.getLogger(__name__)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(request: Request, error: DomainError) -> JSONResponse:
        content: dict[str, object] = {"code": error.code, "message": error.message}
        status_code = 422
        if isinstance(error, (CampaignNotFoundError, FlowNotFoundError, OfferNotFoundError)):
            status_code = 404
        elif isinstance(error, OfferAlreadyExistsError):
            status_code = 409
        elif isinstance(error, CampaignCreationError):
            status_code = 502
            content.update(
                campaign_id=error.campaign_id,
                failed_step=error.failed_step,
                confirmed_flows=error.confirmed_flows,
                upstream_status=error.upstream_status,
                upstream_category=error.upstream_category,
            )
            # Deliberately exclude exception text/traceback, upstream bodies and request data.
            logger.warning(
                "Campaign creation incomplete request_id=%s failed_step=%s "
                "campaign_id=%s confirmed_flows=%s upstream_status=%s upstream_category=%s",
                getattr(request.state, "request_id", None),
                error.failed_step,
                error.campaign_id,
                error.confirmed_flows,
                error.upstream_status,
                error.upstream_category,
            )
        elif isinstance(error, CampaignOffersSaveError):
            status_code = 502
            content.update(
                failed_stream_id=error.failed_stream_id,
                confirmed_stream_ids=error.confirmed_stream_ids,
            )
        elif isinstance(error, TrafficSourceCreationError):
            status_code = 502
            content.update(
                upstream_status=error.upstream_status,
                upstream_category=error.upstream_category,
            )
        return JSONResponse(status_code=status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                # Exclude raw inputs and exception contexts from public errors.
                "errors": [{"loc": item["loc"], "message": item["msg"]} for item in error.errors()],
            },
        )

    @app.exception_handler(KeitaroError)
    async def keitaro_error(_: Request, error: KeitaroError) -> JSONResponse:
        # Never expose upstream bodies, URLs or exception strings (may contain keys).
        return JSONResponse(
            status_code=503 if isinstance(error, KeitaroUnavailableError) else 502,
            content={
                "code": "KEITARO_UNAVAILABLE",
                "message": "Could not complete the request to Keitaro",
            },
        )
