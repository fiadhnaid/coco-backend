from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime


class SessionCreate(BaseModel):
    """Request model for creating a new session"""
    context: str
    goal: str
    user_name: str
    participants: str = ""
    tone: str = ""


class SessionResponse(BaseModel):
    """Response model for session creation"""
    session_id: str
    message: str


class TranscriptEntry(BaseModel):
    """Model for a single transcript entry"""
    speaker: str
    text: str
    timestamp: str


class FinishResponse(BaseModel):
    """Response model for session completion"""
    stars: List[str]
    wish: str
    filler_percentage: float
    takeaways: List[str]
    summary_bullets: List[str]
    transcript: List[Dict]


class Session:
    """In-memory session model"""
    def __init__(self, session_id: str, context: str, goal: str, user_name: str, participants: str = "", tone: str = ""):
        self.session_id = session_id
        self.context = context
        self.goal = goal
        self.user_name = user_name
        self.participants = participants
        self.tone = tone
        self.transcript: List[Dict] = []
        self.audio_buffer = b""
        self.last_suggestion_time = datetime.utcnow()
        self.conversation_history: List[Dict] = []
        self.created_at = datetime.utcnow().isoformat()
        self.active = False

    def add_transcript_entry(self, speaker: str, text: str) -> Dict:
        """Add an entry to the transcript"""
        entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.transcript.append(entry)
        return entry
