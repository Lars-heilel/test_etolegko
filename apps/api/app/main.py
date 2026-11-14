from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.domain.keitaro.exceptions import (
    DomainError,
    FlowNotFoundError,
    OfferAlreadyExistsError,
    OfferNotFoundError,
)
from app.infrastructure.config import get_settings
from app.infrastructure.database import dispose_engine
from app.presentation.api.router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.exception_handler(DomainError)
    async def domain_error(_: Request, error: DomainError) -> JSONResponse:
        status_code = 422
        if isinstance(error, (FlowNotFoundError, OfferNotFoundError)):
            status_code = 404
        elif isinstance(error, OfferAlreadyExistsError):
            status_code = 409
        return JSONResponse(
            status_code=status_code, content={"code": error.code, "message": error.message}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    # Exclude raw inputs and exception contexts from public errors.
                    "errors": [
                        {"loc": item["loc"], "message": item["msg"]} for item in error.errors()
                    ],
                }
            },
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
