"""
CareerCompass AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded

from backend.api import admin, analysis, careers, chat, profile, resume
from backend.config import get_settings
from backend.limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Starting CareerCompass AI in {settings.app_env} mode")
    yield
    logger.info("Shutting down CareerCompass AI")


# Initialize FastAPI
app = FastAPI(
    title="CareerCompass AI",
    description="AI-powered career guidance platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Attach SlowAPI limiter
app.state.limiter = limiter

# CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_cors_headers(request: Request) -> dict:
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in settings.cors_origins_list or "*" in settings.cors_origins_list:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"
    return headers


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Formats Pydantic validation errors consistently."""
    errors = exc.errors()
    msg = ", ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors]) if errors else str(exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": f"Validation error: {msg}"},
        headers=_get_cors_headers(request),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Formats rate limit exceeded errors consistently with APIResponse."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "message": f"Rate limit exceeded: {exc.detail}",
        },
        headers=_get_cors_headers(request),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unhandled exceptions and prevents stack trace leakage."""
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    msg = str(exc) if not settings.is_production else "An internal server error occurred."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": f"Internal server error: {msg}"},
        headers=_get_cors_headers(request),
    )


# Health Check
@app.get("/api/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}


# Register Routers
app.include_router(profile.router, prefix="/api")
app.include_router(careers.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(resume.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
