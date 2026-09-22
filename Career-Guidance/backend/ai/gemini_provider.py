"""
CareerCompass AI — Real Gemini Provider
Wraps the modern google-genai SDK with:
  - Retry logic with exponential backoff
  - Timeout handling (60s)
  - JSON extraction + Pydantic validation
  - Rate-limit and quota handling with automatic key rotation
  - Never exposes API key to callers
"""
import asyncio
import json
import logging
import re
from typing import Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.ai.errors import (
    GeminiConfigError,
    GeminiError,
    GeminiResponseError,
    GeminiTransientError,
    classify_gemini_error,
    get_safe_error_summary,
)
from backend.ai.key_rotator import (
    DEFAULT_COOLDOWN_SECONDS,
    KeyRotationManager,
    is_quota_or_rate_limit,
    is_rotatable_error,
)
from backend.ai.prompts import (
    CAREER_ANALYSIS_PROMPT_VERSION,
    CAREER_ANALYSIS_SYSTEM,
    RESUME_ANALYSIS_PROMPT_VERSION,
    RESUME_ANALYSIS_SYSTEM,
    ROLE_ROADMAP_PROMPT_VERSION,
    ROLE_ROADMAP_SYSTEM,
    build_career_analysis_prompt,
    build_chatbot_system_prompt,
    build_resume_analysis_prompt,
    build_role_roadmap_prompt,
)
from backend.ai.schemas import CareerAnalysisAIResponse, ResumeAnalysisAIResponse, RoleRoadmapAIResponse
from backend.config import Settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 60
CHAT_TOTAL_BUDGET_SECONDS = 21.0
CHAT_PER_ATTEMPT_TIMEOUT_SECONDS = 12.0
MIN_MEANINGFUL_ATTEMPT_SECONDS = 5.0
DEFAULT_TEMPERATURE = 0.4
DEFAULT_TOP_P = 0.95
DEFAULT_MAX_OUTPUT_TOKENS = 8192


def _extract_json(text: str) -> str:
    """
    Extracts JSON from a response that may contain markdown code fences.
    Handles: ```json ... ```, ``` ... ```, or raw JSON.
    """
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    
    obj_match = re.search(r"\{[\s\S]+\}", text)
    if obj_match:
        return obj_match.group(0).strip()
    
    return text.strip()


def _validate_response(raw_text: str, schema: Type[T]) -> T:
    """
    Parses raw Gemini text → JSON → Pydantic schema.
    Raises GeminiResponseError with clear message on failure.
    """
    json_text = _extract_json(raw_text)
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        raise GeminiResponseError(f"Gemini returned invalid JSON: {e}. Raw: {json_text[:200]}")
    
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        raise GeminiResponseError(f"Gemini response failed schema validation: {e}")


def _clean_chat_response(text: str) -> str:
    """
    Cleans chat response. If Gemini wraps the conversational response
    in JSON (e.g. {"response": "..."} or {"message": "..."}), unwraps the text.
    Otherwise returns the clean text string.
    """
    if not text:
        return ""
    trimmed = text.strip()
    if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("```json") and trimmed.endswith("```")):
        try:
            json_str = _extract_json(trimmed)
            data = json.loads(json_str)
            if isinstance(data, dict):
                for key in ("response", "message", "answer", "content", "recommendation"):
                    if key in data and isinstance(data[key], str) and data[key].strip():
                        return data[key].strip()
        except Exception:
            pass
    return trimmed


class GeminiProvider:
    """
    Real Gemini API provider powered by the modern google-genai SDK.
    Supports backend-only key rotation across multiple configured keys.
    API keys are never passed to or stored by callers or logged.
    """

    def __init__(self, settings: Settings, key_manager: Optional[KeyRotationManager] = None):
        self._settings = settings
        self._model_name = settings.gemini_model
        if key_manager is None:
            self._key_manager = KeyRotationManager(settings.gemini_api_keys)
        else:
            self._key_manager = key_manager
        # Backward compatibility: preserve self._client as primary client for test patches
        self._client = self._key_manager.get_primary_client()

    def _get_generation_config(
        self,
        system_instruction: str,
        json_mode: bool = True,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=DEFAULT_TEMPERATURE,
            top_p=DEFAULT_TOP_P,
            max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

    async def _call_with_retry(
        self,
        prompt: str,
        system_instruction: str,
        json_mode: bool = True,
    ) -> str:
        """
        Calls Gemini with automatic API key rotation across configured keys.
        On transient failures (quota, rate-limit, 503, timeout), immediately tries next key.
        Distinguishes configuration errors (invalid model, invalid key) from transient outages.
        """
        keys = self._settings.gemini_api_keys
        if not keys or all(k == "mock-gemini-key" for k in keys):
            raise GeminiConfigError("Gemini API key is not configured or set to mock")

        config = self._get_generation_config(system_instruction, json_mode=json_mode)
        candidate_slots = self._key_manager.get_candidate_slots()
        last_error: Optional[Exception] = None

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        for slot in candidate_slots:
            # Slot 1 uses self._client directly to preserve mock patches in tests
            client = self._client if slot.slot_number == 1 else self._key_manager.get_client(slot)

            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    logger.info(
                        f"Gemini call attempt using provider key slot {slot.slot_number}/{self._key_manager.total_keys} "
                        f"(attempt {attempt}/{MAX_RETRIES}, model {self._model_name})"
                    )

                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: client.models.generate_content(
                                model=self._model_name,
                                contents=prompt,
                                config=config,
                            )
                        ),
                        timeout=REQUEST_TIMEOUT_SECONDS,
                    )

                    if not response or not response.text:
                        raise ValueError("Gemini returned empty response")

                    self._key_manager.mark_success(slot)
                    logger.info(f"Gemini call succeeded using provider key slot {slot.slot_number}")
                    return response.text

                except Exception as e:
                    last_error = e
                    category = classify_gemini_error(e)

                    # Model unavailable / not found (e.g. 404): non-rotatable configuration error
                    if category == "model_unavailable":
                        logger.error(
                            f"Gemini request failed: model '{self._model_name}' unavailable or not found: {e}"
                        )
                        raise GeminiConfigError(
                            f"Configured Gemini model '{self._model_name}' is not found or unsupported. "
                            "Please configure a supported model such as 'gemini-flash-latest' in GEMINI_MODEL."
                        )

                    # Authentication failure (401/403/invalid key):
                    if category == "authentication_error":
                        logger.error(
                            f"Gemini request failed: authentication error on key slot {slot.slot_number}"
                        )
                        self._key_manager.mark_failure(slot, e)
                        break  # Try next configured key slot if available

                    # Programming or validation error: do not rotate, re-raise immediately
                    if not is_rotatable_error(e):
                        logger.error(f"Non-rotatable error encountered during Gemini call: {e}")
                        raise

                    if is_quota_or_rate_limit(e):
                        logger.warning(
                            f"Gemini request failed: quota/rate limit on key slot {slot.slot_number}"
                        )
                        self._key_manager.mark_failure(slot, e)
                        break  # Immediately rotate to next key without wasting retries

                    logger.warning(f"Gemini error on key slot {slot.slot_number} attempt {attempt}: {e}")
                    if attempt < MAX_RETRIES:
                        wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                        await asyncio.sleep(wait)
                    else:
                        self._key_manager.mark_failure(slot, e)

        # All candidate slots failed
        last_category = classify_gemini_error(last_error) if last_error else "unknown"
        if last_category == "authentication_error":
            raise GeminiConfigError(
                "Gemini authentication failed across configured keys (invalid or revoked API key)."
            )
        if last_category == "model_unavailable":
            raise GeminiConfigError(
                f"Gemini model '{self._model_name}' is unavailable or not found."
            )

        raise GeminiTransientError(
            f"All configured Gemini API keys ({self._key_manager.total_keys}) exhausted or unavailable: "
            f"{get_safe_error_summary(last_error) if last_error else 'service unavailable'}"
        )

    # -----------------------------------------------------------------------
    # Public methods
    # -----------------------------------------------------------------------

    async def analyze_career(
        self,
        profile: dict,
        career_matches: list,
    ) -> CareerAnalysisAIResponse:
        """
        Calls Gemini ONCE for the complete career analysis.
        Returns validated CareerAnalysisAIResponse.
        """
        prompt = build_career_analysis_prompt(profile, career_matches)
        raw = await self._call_with_retry(prompt, CAREER_ANALYSIS_SYSTEM)
        try:
            return _validate_response(raw, CareerAnalysisAIResponse)
        except Exception as e:
            logger.error(f"Career analysis validation failed: {e}")
            raise GeminiResponseError(f"AI response validation failed: {e}")

    async def generate_role_roadmap(
        self,
        student_context: dict,
        selected_career: dict,
    ) -> RoleRoadmapAIResponse:
        """
        Calls Gemini specifically to generate a role-specific learning roadmap
        for the student's selected career.
        Returns validated RoleRoadmapAIResponse.
        """
        prompt = build_role_roadmap_prompt(student_context, selected_career)
        raw = await self._call_with_retry(prompt, ROLE_ROADMAP_SYSTEM)
        try:
            return _validate_response(raw, RoleRoadmapAIResponse)
        except Exception as e:
            logger.error(f"Role roadmap validation failed: {e}")
            raise GeminiResponseError(f"AI response validation failed: {e}")

    async def analyze_resume(
        self,
        resume_text: str,
        profile: dict,
    ) -> ResumeAnalysisAIResponse:
        """
        Analyzes resume text and returns structured feedback.
        """
        prompt = build_resume_analysis_prompt(resume_text, profile)
        raw = await self._call_with_retry(prompt, RESUME_ANALYSIS_SYSTEM)
        try:
            return _validate_response(raw, ResumeAnalysisAIResponse)
        except Exception as e:
            logger.error(f"Resume analysis validation failed: {e}")
            raise GeminiResponseError(f"AI response validation failed: {e}")

    async def chat(
        self,
        message: str,
        profile: dict,
        career_goal: str,
        skill_gaps: list,
        conversation_history: list,
        latest_analysis: Optional[dict] = None,
        assessment_signals: Optional[list] = None,
        resume_context: Optional[dict] = None,
        intent: str = "other",
    ) -> str:
        """
        Sends a chat message to Gemini with student context + conversation history.
        Uses json_mode=False for conversational responses and rotates keys on failure.
        """
        keys = self._settings.gemini_api_keys
        if not keys or all(k == "mock-gemini-key" for k in keys):
            raise GeminiConfigError("Gemini API key is not configured or set to mock")

        system_prompt = build_chatbot_system_prompt(
            profile,
            career_goal,
            skill_gaps,
            latest_analysis=latest_analysis,
            assessment_signals=assessment_signals,
            resume_context=resume_context,
            intent=intent,
        )
        config = self._get_generation_config(system_prompt, json_mode=False)

        limited_history = conversation_history[-10:] if conversation_history else []
        history_contents: list[types.Content] = []
        for msg in limited_history:
            content_text = (msg.get("content") or "").strip()
            if not content_text:
                continue
            role = "model" if msg.get("role") in ("assistant", "model") else "user"
            history_contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content_text)]
                )
            )

        # Gemini requires that history turns start with a user turn
        while history_contents and history_contents[0].role == "model":
            history_contents.pop(0)

        # Merge adjacent turns with identical roles
        merged_history: list[types.Content] = []
        for content in history_contents:
            if merged_history and merged_history[-1].role == content.role:
                merged_history[-1].parts.extend(content.parts)
            else:
                merged_history.append(content)
        history_contents = merged_history

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        deadline = loop.time() + CHAT_TOTAL_BUDGET_SECONDS
        candidate_slots = self._key_manager.get_candidate_slots()
        last_error: Optional[Exception] = None

        for slot in candidate_slots:
            remaining = deadline - loop.time()
            if remaining < MIN_MEANINGFUL_ATTEMPT_SECONDS:
                logger.warning(
                    f"Chat remaining budget ({remaining:.1f}s) is below minimum meaningful attempt ({MIN_MEANINGFUL_ATTEMPT_SECONDS}s); stopping rotation."
                )
                break

            client = self._client if slot.slot_number == 1 else self._key_manager.get_client(slot)

            for attempt in range(1, MAX_RETRIES + 1):
                remaining = deadline - loop.time()
                if remaining < MIN_MEANINGFUL_ATTEMPT_SECONDS:
                    logger.warning(
                        f"Chat remaining budget ({remaining:.1f}s) on slot {slot.slot_number}, attempt {attempt} "
                        f"is below minimum meaningful attempt ({MIN_MEANINGFUL_ATTEMPT_SECONDS}s); triggering fallback."
                    )
                    break

                per_attempt_timeout = min(
                    CHAT_PER_ATTEMPT_TIMEOUT_SECONDS,
                    max(1.0, remaining - 0.5),
                )

                try:
                    logger.info(
                        f"Gemini chat attempt using provider key slot {slot.slot_number}/{self._key_manager.total_keys} "
                        f"(attempt {attempt}/{MAX_RETRIES}, timeout={per_attempt_timeout:.1f}s, remaining={remaining:.1f}s)"
                    )
                    def _send_chat_call(c, model, cfg, hist, msg, timeout_sec):
                        cfg.http_options = types.HttpOptions(timeout=int(timeout_sec * 1000))
                        session = c.chats.create(
                            model=model,
                            config=cfg,
                            history=hist,
                        )
                        return session.send_message(msg)

                    response = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: _send_chat_call(
                                client,
                                self._model_name,
                                config,
                                history_contents,
                                message,
                                per_attempt_timeout,
                            )
                        ),
                        timeout=per_attempt_timeout,
                    )
                    if not response or not response.text:
                        raise ValueError("Gemini returned empty response")
                    self._key_manager.mark_success(slot)
                    return _clean_chat_response(response.text)
                except Exception as e:
                    last_error = e
                    category = classify_gemini_error(e)
                    logger.warning(
                        f"Gemini chat failed on slot {slot.slot_number}, attempt {attempt}/{MAX_RETRIES}: "
                        f"{category} ({e})"
                    )
                    if category == "model_unavailable":
                        raise GeminiConfigError(
                            f"Configured Gemini model '{self._model_name}' is not found or unsupported."
                        )
                    if not is_rotatable_error(e):
                        raise
                    if is_quota_or_rate_limit(e):
                        logger.warning(f"Slot {slot.slot_number} hit quota/rate-limit in chat; rotating to next slot.")
                        break

                    # Check remaining time before backoff sleep
                    remaining_after_err = deadline - loop.time()
                    if attempt < MAX_RETRIES:
                        wait = BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                        # Only sleep if remaining budget leaves enough time for another meaningful attempt
                        if remaining_after_err > wait + MIN_MEANINGFUL_ATTEMPT_SECONDS:
                            await asyncio.sleep(wait)
                        else:
                            logger.warning(
                                f"Skipping backoff sleep ({wait:.1f}s) as remaining budget ({remaining_after_err:.1f}s) "
                                f"leaves less than {MIN_MEANINGFUL_ATTEMPT_SECONDS}s for a retry."
                            )
                            if remaining_after_err < MIN_MEANINGFUL_ATTEMPT_SECONDS:
                                break

            self._key_manager.mark_failure(slot, last_error)
            if deadline - loop.time() < MIN_MEANINGFUL_ATTEMPT_SECONDS:
                logger.warning("Chat remaining budget below threshold after slot failure; stopping key rotation.")
                break

        logger.error(f"Chat error across all configured keys or deadline expired: {last_error}")
        raise RuntimeError(f"AI chat temporarily unavailable across keys: {last_error}")

    @property
    def career_analysis_prompt_version(self) -> str:
        return CAREER_ANALYSIS_PROMPT_VERSION

    @property
    def resume_analysis_prompt_version(self) -> str:
        return RESUME_ANALYSIS_PROMPT_VERSION

    @property
    def role_roadmap_prompt_version(self) -> str:
        return ROLE_ROADMAP_PROMPT_VERSION

    @property
    def model_name(self) -> str:
        return self._model_name
