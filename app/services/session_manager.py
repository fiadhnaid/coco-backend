from typing import Dict, Optional
import uuid
from app.models.session import Session


class SessionManager:
    """Manages conversation sessions"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(self, context: str, goal: str, user_name: str, participants: str = "", tone: str = "") -> str:
        """Create a new session and return its ID"""
        session_id = str(uuid.uuid4())
        session = Session(session_id, context, goal, user_name, participants, tone)
        self._sessions[session_id] = session
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists"""
        return session_id in self._sessions


# Global session manager instance
session_manager = SessionManager()
