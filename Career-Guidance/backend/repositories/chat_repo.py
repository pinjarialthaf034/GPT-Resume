"""
CareerCompass AI — Chat Repository
Stores chat sessions and messages.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from supabase import Client

logger = logging.getLogger(__name__)


class ChatRepository:
    def __init__(self, db: Client):
        self._db = db

    def get_or_create_session(self, profile_id: str, session_id: Optional[str] = None) -> Dict:
        """Gets an existing session or creates a new one."""
        if session_id:
            result = (
                self._db.table("chat_sessions")
                .select("*")
                .eq("id", session_id)
                .eq("profile_id", profile_id)  # Ensures student can only access their own
                .single()
                .execute()
            )
            if result.data:
                return result.data

        # Create new session
        payload = {
            "profile_id": profile_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self._db.table("chat_sessions").insert(payload).execute()
        return result.data[0] if result.data else {}

    def list_sessions(self, profile_id: str) -> List[Dict]:
        result = (
            self._db.table("chat_sessions")
            .select("id, created_at, updated_at")
            .eq("profile_id", profile_id)
            .order("updated_at", desc=True)
            .limit(20)
            .execute()
        )
        return result.data or []

    def get_messages(self, session_id: str, profile_id: str, limit: int = 50) -> List[Dict]:
        """Gets messages — validates profile ownership."""
        # Validate session belongs to this profile
        session = (
            self._db.table("chat_sessions")
            .select("id")
            .eq("id", session_id)
            .eq("profile_id", profile_id)
            .single()
            .execute()
        )
        if not session.data:
            return []

        result = (
            self._db.table("chat_messages")
            .select("id, role, content, created_at")
            .eq("session_id", session_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def save_message(self, session_id: str, role: str, content: str) -> Dict:
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self._db.table("chat_messages").insert(payload).execute()
        # Update session updated_at
        self._db.table("chat_sessions").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", session_id).execute()
        return result.data[0] if result.data else {}
