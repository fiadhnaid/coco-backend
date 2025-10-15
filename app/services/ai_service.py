import os
import io
import wave
import json
import base64
from typing import Dict, List
from openai import OpenAI
from elevenlabs.client import ElevenLabs


class AIService:
    """Service for AI operations (OpenAI + ElevenLabs)"""

    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    def transcribe_audio(self, audio_data: bytes) -> str:
        """Transcribe audio using OpenAI Whisper"""
        # Convert PCM to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_data)

        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"

        # Transcribe
        transcription = self.openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=wav_buffer,
            language="en"
        )

        return transcription.text.strip()

    def generate_coaching_suggestion(
        self,
        user_name: str,
        context: str,
        goal: str,
        conversation_history: List[Dict]
    ) -> str:
        """Generate a coaching suggestion using GPT-4"""
        prompt = f"""You are a conversation coach helping {user_name}.

Context: {context}
Goal: {goal}

Recent conversation:
{' '.join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]])}

Provide ONE short, actionable coaching tip (max 10 words) to help them achieve their goal. Be encouraging and specific."""

        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful conversation coach. Give brief, actionable tips."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=50,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    def generate_tts_audio(self, text: str) -> str:
        """Generate speech audio using ElevenLabs, returns base64"""
        audio_response = self.elevenlabs_client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice
            text=text,
            model_id="eleven_turbo_v2_5"
        )

        # Collect audio bytes
        audio_bytes = b""
        for chunk in audio_response:
            audio_bytes += chunk

        # Return as base64
        return base64.b64encode(audio_bytes).decode('utf-8')

    def analyze_session(
        self,
        user_name: str,
        context: str,
        goal: str,
        transcript: List[Dict]
    ) -> Dict:
        """Analyze session and generate feedback"""
        transcript_text = "\n".join([
            f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}"
            for entry in transcript
        ])

        if not transcript_text.strip():
            return {
                "stars": ["Started the session", "Ready to practice"],
                "wish": "Have a longer conversation to get more feedback",
                "filler_percentage": 0.0,
                "takeaways": [
                    "Practice makes perfect",
                    "Try again with a real conversation",
                    "Focus on your goals"
                ],
                "summary_bullets": ["Session started but no conversation recorded"]
            }

        prompt = f"""You are analyzing a conversation coaching session.

User Details:
- Name: {user_name}
- Context: {context}
- Goal: {goal}

Full Transcript:
{transcript_text}

Analyze ONLY the user's speech (name: {user_name}). Provide:

1. Two stars (2 things they did well)
2. One wish (1 area for improvement)
3. Filler percentage (% of their words that were filler like "um", "uh", "like", "you know")
4. Three key takeaways
5. 3-5 summary bullets of the conversation

Return as JSON:
{{
    "stars": ["star 1", "star 2"],
    "wish": "one wish",
    "filler_percentage": 5.2,
    "takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
    "summary_bullets": ["bullet 1", "bullet 2", "bullet 3"]
}}
"""

        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a conversation coach providing feedback. Always respond with valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)


# Global AI service instance
ai_service = AIService()
