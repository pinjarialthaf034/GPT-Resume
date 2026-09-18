"""
CareerCompass AI — Shared FastAPI Dependencies
Provides Supabase client and verified Supabase Auth JWT identity resolution.
Strictly isolates student data by canonical auth.users.id.
Zero default/demo profile fallback.
"""
import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from supabase import Client, create_client

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Security scheme for Bearer token extraction
security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# User Identity Models
# ---------------------------------------------------------------------------

class AuthenticatedUser(BaseModel):
    """
    Verified Supabase Auth user identity.
    Derived exclusively from cryptographically validated JWT session.
    """
    id: str = Field(..., description="Canonical Supabase Auth UUID (auth.users.id)")
    email: str = Field(..., description="User email address")
    is_admin: bool = Field(False, description="Whether user holds administrative privileges")
    app_metadata: Dict[str, Any] = Field(default_factory=dict)
    user_metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Supabase clients
# ---------------------------------------------------------------------------

@lru_cache()
def _create_cached_client(url: str, key: str) -> Client:
    return create_client(url, key)


def _get_anon_client(settings: Settings) -> Client:
    """Anon-key client — respects RLS."""
    return _create_cached_client(settings.supabase_url, settings.supabase_anon_key)


def _get_service_client(settings: Settings) -> Client:
    """Service-role client — bypasses RLS. Used in verified backend services."""
    return _create_cached_client(settings.supabase_url, settings.supabase_service_role_key)


def get_anon_supabase(settings: Settings = Depends(get_settings)) -> Client:
    return _get_anon_client(settings)


def get_service_supabase(settings: Settings = Depends(get_settings)) -> Client:
    return _get_service_client(settings)


# ---------------------------------------------------------------------------
# Canonical Authentication & Authorization Dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
    anon_client: Client = Depends(get_anon_supabase),
    service_client: Client = Depends(get_service_supabase),
) -> AuthenticatedUser:
    """
    Authenticates every protected request using verified Supabase Auth JWT.
    Validates token against Supabase Auth server.
    Extracts authenticated user ID.
    Returns HTTP 401 if missing, invalid, or expired.
    Never falls back to demo, default, or client-supplied IDs.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty authentication token provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth_response = anon_client.auth.get_user(token)
        if not auth_response or not auth_response.user or not auth_response.user.id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication session.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = auth_response.user
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Supabase Auth verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Token could not be validated with Supabase.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = str(user.id)
    user_email = str(getattr(user, "email", "") or "")

    # Admin authorization check: app_metadata, user_metadata, or verified database role
    app_meta = getattr(user, "app_metadata", {}) or {}
    user_meta = getattr(user, "user_metadata", {}) or {}
    is_admin = bool(
        app_meta.get("is_admin") 
        or user_meta.get("is_admin") 
        or app_meta.get("role") == "admin"
    )

    if not is_admin:
        try:
            profile_res = (
                service_client.table("profiles")
                .select("is_admin")
                .eq("id", user_id)
                .maybe_single()
                .execute()
            )
            if profile_res and profile_res.data:
                is_admin = bool(profile_res.data.get("is_admin", False))
        except Exception:
            pass

    return AuthenticatedUser(
        id=user_id,
        email=user_email,
        is_admin=is_admin,
        app_metadata=app_meta if isinstance(app_meta, dict) else {},
        user_metadata=user_meta if isinstance(user_meta, dict) else {},
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
    anon_client: Client = Depends(get_anon_supabase),
    service_client: Client = Depends(get_service_supabase),
) -> Optional[AuthenticatedUser]:
    """
    Returns AuthenticatedUser if valid token is provided, else None.
    Used for endpoints that provide enriched experience to authenticated users without blocking others.
    """
    if not credentials or not credentials.credentials:
        return None
    try:
        return await get_current_user(
            credentials=credentials,
            settings=settings,
            anon_client=anon_client,
            service_client=service_client,
        )
    except HTTPException:
        return None


async def require_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Enforces that the authenticated user possesses administrator privileges.
    Returns HTTP 401 if unauthenticated (via get_current_user).
    Returns HTTP 403 if authenticated but not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authorization required. You do not have permission to access this resource.",
        )
    return current_user
