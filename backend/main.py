"""FastAPI backend for Ghosted Cloud AI."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv
import time
import uuid
import os
from routes.ai import router as ai_router
from routes.advanced_ai import router as advanced_ai_router
from routes.conversational_ai import router as conversational_ai_router
from routes.ec2 import router as ec2_router
from routes.direct_ec2 import router as direct_ec2_router
from routes.direct_s3 import router as direct_s3_router
from utils.logging_config import configure_logging, bind_request_context

logger = configure_logging()
load_dotenv()

app = FastAPI(title="Ghosted Cloud AI API")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://frontend:3000",
]


def get_allowed_origins() -> list[str]:
    configured_origins = os.environ.get("CORS_ORIGINS")
    if not configured_origins:
        return DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


allowed_origins = get_allowed_origins()
allow_all_origins = "*" in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else allowed_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

from utils.rate_limiter import RateLimiter
rate_limiter = RateLimiter()


@app.middleware("http")
async def add_request_tracking(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    log = bind_request_context(logger, request_id)

    user_id = request.headers.get("X-User-ID", "anonymous")
    client_ip = request.client.host if request.client else None
    endpoint = request.url.path

    if not endpoint.startswith(("/docs", "/redoc", "/openapi.json", "/static")):
        allowed, retry_after = rate_limiter.check_rate_limit(user_id, endpoint, client_ip)
        if not allowed:
            log.warning("Rate limit exceeded", user_id=user_id, ip=client_ip, endpoint=endpoint)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {"code": 429, "message": "Rate limit exceeded. Please try again later.", "type": "rate_limit_error"},
                    "retry_after": retry_after,
                    "request_id": request_id,
                },
                headers={"Retry-After": str(retry_after)},
            )

    log.info("Request started", method=request.method, path=request.url.path)
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log.info("Request completed", status_code=response.status_code, process_time_ms=round(process_time * 1000, 2))
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        log.error("Request failed", error=str(e), error_type=type(e).__name__, process_time_ms=round(process_time * 1000, 2))
        raise


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = request.headers.get("X-Request-ID", None)
    log = bind_request_context(logger, request_id)
    log.error("HTTP exception", status_code=exc.status_code, detail=str(exc.detail), path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": str(exc.detail), "type": "http_error"}, "request_id": request_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID", None)
    log = bind_request_context(logger, request_id)
    errors = exc.errors()
    log.error("Validation error", errors=errors, path=request.url.path)

    user_friendly_errors = []
    for error in errors:
        field = ".".join([str(loc) for loc in error["loc"][1:]])
        prefix = "" if error["loc"][0] == "body" else f"{error['loc'][0]} parameter "
        user_friendly_errors.append(f"Invalid {prefix}'{field}': {error['msg']}")

    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": 422, "message": "Validation Error", "details": user_friendly_errors, "type": "validation_error"},
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", None)
    log = bind_request_context(logger, request_id)
    log.error("Unhandled exception", error_type=type(exc).__name__, error_message=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": 500, "message": "An unexpected error occurred.", "type": "server_error"}, "request_id": request_id},
    )


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0-beta", "timestamp": time.time()}


app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(advanced_ai_router, prefix="/api/advanced-ai", tags=["advanced-ai"])
app.include_router(conversational_ai_router, prefix="/api/conversational-ai", tags=["conversational-ai"])
app.include_router(ec2_router, prefix="/api/ec2", tags=["ec2"])
app.include_router(direct_ec2_router, prefix="/api/direct/ec2", tags=["direct_ec2"])
app.include_router(direct_s3_router, prefix="/api/direct/s3", tags=["direct_s3"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
