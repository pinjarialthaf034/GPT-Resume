"""
CareerCompass AI — Gemini Error Hierarchy & Classification
Provides structured, safe exception handling and classification for Gemini operations.
Guarantees secrets and API keys are NEVER included in error messages or logs.
"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiError(RuntimeError):
    """Base exception for all Gemini-related errors."""
    pass


class GeminiConfigError(GeminiError):
    """
    Raised when Gemini configuration is invalid:
    - Missing or unconfigured API key
    - Invalid or revoked API key / authentication failure (401/403)
    - Model not found / deprecated / unavailable (404)
    Non-rotatable. Should NOT be hidden as a temporary outage.
    """
    pass


class GeminiTransientError(GeminiError):
    """
    Raised when Gemini is temporarily unavailable across all rotatable keys:
    - Quota exceeded (429 / RESOURCE_EXHAUSTED)
    - Service unavailable / server overload (500, 502, 503, 504)
    - Network timeout / connection drop
    Rotatable across keys; triggers deterministic fallback when all keys exhausted.
    """
    pass


class GeminiResponseError(GeminiError):
    """
    Raised when Gemini response cannot be parsed or fails schema validation.
    Non-rotatable (indicates prompt, parsing, or schema issue).
    """
    pass


def classify_gemini_error(exc: Exception) -> str:
    """
    Classifies an exception into a structured category for logging and routing.
    Never exposes raw API keys, credentials, or headers.

    Categories:
      - "missing_key"
      - "authentication_error"
      - "model_unavailable"
      - "quota_rate_limit"
      - "transient_server"
      - "network_timeout"
      - "parsing_error"
      - "programming_error"
      - "unknown"
    """
    if exc is None:
        return "unknown"

    if isinstance(exc, (TypeError, KeyError, AttributeError, IndexError)):
        return "programming_error"

    type_name = type(exc).__name__.lower()
    if "validation" in type_name or "decode" in type_name:
        return "parsing_error"

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return "network_timeout"

    err_str = str(exc).lower()

    # Check for missing/mock key
    if "mock-gemini-key" in err_str or "key is not configured" in err_str or "api key missing" in err_str:
        return "missing_key"

    # Check status codes if present on exception object
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code == 404:
        return "model_unavailable"
    if status_code in (401, 403):
        return "authentication_error"
    if status_code == 429:
        return "quota_rate_limit"
    if status_code in (500, 502, 503, 504):
        return "transient_server"

    # Check string patterns for model not found / deprecated
    if "not found" in err_str or "not_found" in err_str or "404" in err_str:
        if "model" in err_str or "models/" in err_str:
            return "model_unavailable"

    # Check string patterns for authentication / API key invalid
    auth_patterns = (
        "api_key_invalid",
        "api key not valid",
        "invalid api key",
        "permission_denied",
        "permission denied",
        "unauthenticated",
        "consumer_invalid",
        "401",
        "403",
    )
    if any(p in err_str for p in auth_patterns):
        return "authentication_error"

    # Check string patterns for quota / rate limits
    quota_patterns = (
        "429",
        "resource_exhausted",
        "resource exhausted",
        "quota",
        "rate limit",
        "ratelimit",
        "rate_limit",
        "too many requests",
    )
    if any(p in err_str for p in quota_patterns):
        return "quota_rate_limit"

    # Check string patterns for server overload / unavailable
    server_patterns = (
        "500",
        "502",
        "503",
        "504",
        "server error",
        "unavailable",
        "overloaded",
        "internal error",
        "bad gateway",
    )
    if any(p in err_str for p in server_patterns):
        return "transient_server"

    # Check string patterns for network / timeout
    timeout_patterns = (
        "timed out",
        "timeout",
        "deadline",
        "connection error",
        "connection reset",
        "remote end closed",
    )
    if any(p in err_str for p in timeout_patterns):
        return "network_timeout"

    if "validation failed" in err_str or "invalid json" in err_str or "jsondecodeerror" in err_str:
        return "parsing_error"

    return "unknown"


def get_safe_error_summary(exc: Exception) -> str:
    """Returns a safe, high-level summary string without any secrets or credentials."""
    category = classify_gemini_error(exc)
    mapping = {
        "missing_key": "Gemini API key is not configured or set to mock",
        "authentication_error": "Gemini authentication failed (invalid or revoked API key)",
        "model_unavailable": "Gemini model is unavailable or not found for this API version",
        "quota_rate_limit": "Gemini quota exceeded or rate limit hit",
        "transient_server": "Gemini server temporarily unavailable or overloaded",
        "network_timeout": "Gemini request timed out or connection dropped",
        "parsing_error": "Gemini response parsing or schema validation failed",
        "programming_error": "Application programming error during Gemini invocation",
        "unknown": f"Gemini request failed: {type(exc).__name__}",
    }
    return mapping.get(category, "Gemini request failed")
