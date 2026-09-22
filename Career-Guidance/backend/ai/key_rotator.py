"""
CareerCompass AI — Key Rotation Manager
Provides backend-only Gemini API key rotation, cooldown for rate limits/quota exhaustion,
and safe slot-based logging without ever exposing credentials.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from google import genai

from backend.ai.errors import (
    classify_gemini_error,
    get_safe_error_summary,
)

logger = logging.getLogger(__name__)

# Default cooldown for quota exhaustion / rate limits: 300 seconds (5 minutes)
DEFAULT_COOLDOWN_SECONDS = 300.0


def is_rotatable_error(exc: Exception) -> bool:
    """
    Determines if an exception is an appropriate transient/provider error
    that should trigger key rotation.

    Rotatable:
      - HTTP 429, RESOURCE_EXHAUSTED, Quota Exceeded, Rate Limit
      - HTTP 500, 502, 503, 504, Server Errors, Overloaded, Unavailable
      - TimeoutError, asyncio.TimeoutError, Deadline Exceeded, Network drops

    Non-Rotatable:
      - Configuration errors (Missing key, Invalid API key / 401/403, Invalid/404 Model)
      - Programming errors (TypeError, KeyError, AttributeError, IndexError)
      - Validation errors (Pydantic ValidationError, invalid student input, JSON parse error)
    """
    category = classify_gemini_error(exc)
    return category in ("quota_rate_limit", "transient_server", "network_timeout")


def is_quota_or_rate_limit(exc: Exception) -> bool:
    """Checks if failure was specifically quota exhaustion or rate limiting."""
    return classify_gemini_error(exc) == "quota_rate_limit"


def is_overloaded_or_unavailable(exc: Exception) -> bool:
    """Checks if failure was specifically server overload, 503 unavailable, or transient server error."""
    return classify_gemini_error(exc) == "transient_server"


class KeySlot:
    """Represents a configured API key slot."""
    def __init__(self, slot_number: int, key: str):
        self.slot_number = slot_number  # 1-based index (e.g. 1, 2, 3)
        self.key = key
        self.cooldown_until = 0.0
        self.failure_count = 0

    @property
    def is_cooling_down(self) -> bool:
        return time.time() < self.cooldown_until

    def trigger_cooldown(self, seconds: float = DEFAULT_COOLDOWN_SECONDS):
        self.cooldown_until = time.time() + seconds
        self.failure_count += 1

    def record_failure(self):
        self.failure_count += 1

    def record_success(self):
        self.failure_count = 0
        self.cooldown_until = 0.0


class KeyRotationManager:
    """
    Thread-safe / async-safe manager for multiple Gemini API keys.
    Maintains slots, handles cooldowns, and caches genai.Client instances.
    Never logs or exposes actual API keys.
    """

    def __init__(self, keys: List[str], cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS):
        # Clean and deduplicate keys while preserving order
        cleaned: List[str] = []
        for k in keys:
            k = (k or "").strip().strip("'\"").strip()
            if k and k not in cleaned:
                cleaned.append(k)

        if not cleaned:
            cleaned = ["mock-gemini-key"]

        self._slots: List[KeySlot] = [
            KeySlot(slot_number=idx + 1, key=k)
            for idx, k in enumerate(cleaned)
        ]
        self._cooldown_seconds = cooldown_seconds
        self._clients: Dict[int, genai.Client] = {}
        self._lock = asyncio.Lock()

    @property
    def total_keys(self) -> int:
        return len(self._slots)

    def get_client(self, slot: KeySlot) -> genai.Client:
        """Returns or creates a cached genai.Client for the given slot."""
        if slot.slot_number not in self._clients:
            self._clients[slot.slot_number] = genai.Client(api_key=slot.key)
        return self._clients[slot.slot_number]

    def get_primary_client(self) -> genai.Client:
        """Returns client for Slot 1 for backward compatibility."""
        return self.get_client(self._slots[0])

    def get_candidate_slots(self) -> List[KeySlot]:
        """
        Returns eligible key slots in priority order:
        - First, slots not currently in cooldown.
        - If all slots are in cooldown, returns slots sorted by earliest cooldown expiry
          to avoid blocking indefinitely.
        """
        active_slots = [s for s in self._slots if not s.is_cooling_down]
        if active_slots:
            return active_slots

        # If all slots are in cooldown, sort by nearest expiry
        return sorted(self._slots, key=lambda s: s.cooldown_until)

    def mark_success(self, slot: KeySlot):
        """Marks a key attempt as successful."""
        slot.record_success()

    def mark_failure(self, slot: KeySlot, exc: Exception) -> bool:
        """
        Records failure and determines if key should be placed into cooldown.
        Logs safe message without sensitive data.
        Returns True if error was rotatable.
        """
        category = classify_gemini_error(exc)
        if not is_rotatable_error(exc):
            logger.warning(
                f"Gemini provider key slot {slot.slot_number} encountered non-rotatable error: "
                f"{get_safe_error_summary(exc)}"
            )
            return False

        if category == "quota_rate_limit":
            slot.trigger_cooldown(self._cooldown_seconds)
            logger.warning(
                f"Gemini provider attempt {slot.slot_number} failed (quota/rate-limit cooldown for {self._cooldown_seconds}s); trying next configured provider key."
            )
        elif category == "network_timeout":
            slot.record_failure()
            logger.warning(
                f"Gemini provider attempt {slot.slot_number} failed (network timeout); trying next configured provider key."
            )
        else:
            slot.record_failure()
            logger.warning(
                f"Gemini provider attempt {slot.slot_number} failed (transient server error); trying next configured provider key."
            )

        return True

    def get_health_status(self) -> List[Dict[str, Any]]:
        """Returns safe diagnostic information about slots without exposing keys."""
        now = time.time()
        return [
            {
                "slot_number": s.slot_number,
                "is_cooling_down": s.is_cooling_down,
                "cooldown_remaining_seconds": max(0.0, round(s.cooldown_until - now, 1)),
                "failure_count": s.failure_count,
            }
            for s in self._slots
        ]
