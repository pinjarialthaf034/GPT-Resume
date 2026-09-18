"""
CareerCompass AI — Application Configuration
Loads all settings from environment variables via Pydantic Settings and python-dotenv.
Never hard-codes secrets or credentials.
"""
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

from dotenv import dotenv_values, find_dotenv, load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Proactively load .env into os.environ at module import time
_env_path = find_dotenv(usecwd=True)
if _env_path:
    load_dotenv(_env_path, override=False)


def _clean_key(raw: Optional[str]) -> Optional[str]:
    """Strips whitespace and surrounding single/double quotes."""
    if not raw:
        return None
    cleaned = raw.strip().strip("'\"").strip()
    return cleaned if cleaned else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Supabase ---
    supabase_url: str = "https://mock.supabase.co"
    supabase_anon_key: str = "mock-anon-key"
    supabase_service_role_key: str = "mock-service-role-key"

    # --- Google Gemini ---
    gemini_api_key: str = "mock-gemini-key"
    gemini_api_keys_raw: Optional[str] = None  # Comma-separated or GEMINI_API_KEYS
    gemini_model: str = "gemini-3.6-flash"

    # --- App ---
    app_env: str = "development"
    app_secret_key: str = "change-this-to-a-long-random-secret"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:5500,http://localhost:5500,http://localhost:8000,http://127.0.0.1:8000,http://localhost:8001,http://127.0.0.1:8001,https://gpt-career.netlify.app,https://gpt-resume.netlify.app"

    # --- AI Rate Limits (per user per hour) ---
    ai_career_analysis_rate_limit: int = 3
    ai_resume_analysis_rate_limit: int = 5
    ai_chat_rate_limit: int = 30

    # --- Chat ---
    chat_max_context_tokens: int = 2000

    # --- Resume ---
    max_resume_size_mb: int = 5

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def gemini_api_keys(self) -> List[str]:
        """
        Discovers all configured Gemini API keys in priority order:
        1. Numbered environment variables: GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3...
           (checked from both os.environ and directly from .env file)
        2. GEMINI_API_KEYS (comma-separated list if provided in env/settings)
        3. GEMINI_API_KEY (primary/fallback)
        Deduplicates while preserving priority order and stripping whitespace/quotes.
        """
        discovered: List[str] = []

        # Combine os.environ and direct .env file values so .env changes are never missed
        combined_sources: Dict[str, str] = {}
        if _env_path and os.path.exists(_env_path):
            try:
                for k, v in dotenv_values(_env_path).items():
                    if k and v:
                        combined_sources[k] = v
            except Exception:
                pass
        # os.environ takes precedence if explicitly exported in the environment
        for k, v in os.environ.items():
            if k and v:
                combined_sources[k] = v

        # 1. Numbered environment variables: GEMINI_API_KEY_1, GEMINI_API_KEY_2, ...
        numbered_keys = []
        for key, value in combined_sources.items():
            match = re.match(r"^GEMINI_API_KEY_(\d+)$", key.upper())
            if match:
                cleaned = _clean_key(value)
                if cleaned:
                    index = int(match.group(1))
                    numbered_keys.append((index, cleaned))
        numbered_keys.sort(key=lambda x: x[0])
        for _, val in numbered_keys:
            if val not in discovered:
                discovered.append(val)

        # 2. Comma-separated GEMINI_API_KEYS or gemini_api_keys_raw
        raw_list = combined_sources.get("GEMINI_API_KEYS") or self.gemini_api_keys_raw
        if raw_list:
            for k in raw_list.split(","):
                cleaned = _clean_key(k)
                if cleaned and cleaned not in discovered:
                    discovered.append(cleaned)

        # 3. Base GEMINI_API_KEY
        base_key = _clean_key(combined_sources.get("GEMINI_API_KEY") or self.gemini_api_key)
        if base_key and base_key not in discovered:
            discovered.append(base_key)

        # If real keys were discovered, remove "mock-gemini-key"
        real_keys = [k for k in discovered if k != "mock-gemini-key"]
        if real_keys:
            # Sync primary self.gemini_api_key for single-key consumers
            if self.gemini_api_key == "mock-gemini-key" or not self.gemini_api_key:
                self.gemini_api_key = real_keys[0]
            return real_keys

        return ["mock-gemini-key"]

    def get_gemini_diagnostics(self) -> Dict[str, Any]:
        """
        Returns safe, structured Gemini configuration status.
        NEVER includes raw or partial API keys, headers, or credentials.
        """
        keys = self.gemini_api_keys
        real_keys = [k for k in keys if k and k != "mock-gemini-key"]
        is_configured = len(real_keys) > 0
        return {
            "configured": is_configured,
            "key_count": len(real_keys),
            "active_key_index": 1 if is_configured else 0,
            "key_source": (
                "GEMINI_API_KEY_1" if len(real_keys) > 1
                else ("GEMINI_API_KEY" if real_keys else "unconfigured")
            ),
            "model": self.gemini_model,
        }

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def max_resume_size_bytes(self) -> int:
        return self.max_resume_size_mb * 1024 * 1024

    @field_validator("supabase_url")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with https://")
        app_env = os.getenv("APP_ENV", "development").lower()
        if app_env == "production" and "mock.supabase.co" in v:
            raise ValueError("SUPABASE_URL cannot be mock.supabase.co in production environment. Real Supabase URL is required.")
        return v

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        if not v:
            raise ValueError("GEMINI_API_KEY must not be empty")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — loads once per process."""
    return Settings()


def reload_settings() -> Settings:
    """
    Clears cached settings, reloads .env into os.environ, and returns a fresh Settings instance.
    Useful when .env is updated without a full process restart.
    """
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=True)
    get_settings.cache_clear()
    return get_settings()
