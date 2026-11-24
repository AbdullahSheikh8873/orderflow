"""OrderFlow FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.logging_config import configure_logging, get_logger
from app.routers import admin, auth, orders, pages, products

settings = get_settings()
configure_logging("DEBUG" if settings.debug else "INFO")
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "OrderFlow starting up",
        extra={"data": {"environment": settings.environment, "aws_disabled": settings.aws_disabled}},
    )
    yield
    logger.info("OrderFlow shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Event-driven E-Commerce Order Management System (FastAPI + PostgreSQL + AWS SQS/SNS/S3/Lambda).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(pages.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = jsonable_encoder(exc.errors())
    logger.warning("Validation error", extra={"data": {"path": str(request.url), "errors": errors}})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )


@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}
