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

    def transcribe_audio(
        self,
        audio_data: bytes,
        prompt: str = None,
        context: str = None,
        goal: str = None
    ) -> str:
        """
        Transcribe audio using OpenAI's gpt-4o-mini-transcribe model.

        Args:
            audio_data: Raw PCM audio bytes
            prompt: Optional context to improve transcription accuracy
            context: Conversation context (used to build prompt)
            goal: User's goal (used to build prompt)

        Returns:
            Transcribed text
        """
        # Convert PCM to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(16000)
            wav_file.writeframes(audio_data)

        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"

        # Build context prompt if available to improve accuracy
        # Per OpenAI docs: prompts help with uncommon words, acronyms, and context
        transcription_prompt = prompt
        if not transcription_prompt and (context or goal):
            prompt_parts = []
            if context:
                prompt_parts.append(f"Context: {context}")
            if goal:
                prompt_parts.append(f"Goal: {goal}")
            transcription_prompt = "Okay, here's what I'm, like, thinking.. You're going to transcribe this conversation. Here's some context on the conversation ".join(prompt_parts) + "."

        # Transcribe with optional prompt for better accuracy
        transcription = self.openai_client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=wav_buffer,
            language="en",
            response_format="text",
            prompt=transcription_prompt if transcription_prompt else None
        )

        return transcription.strip()

    def generate_coaching_suggestion(
        self,
        user_name: str,
        context: str,
        goal: str,
        conversation_history: List[Dict],
        participants: str = "",
        tone: str = ""
    ) -> str:
        """Generate a coaching suggestion using GPT-4"""
        # Build system prompt with user context and information
        system_prompt = f"""You are an expert conversation coach helping {user_name} achieve their desired outcome from this conversation by coaching, prompting and guiding them in real time during the conversation.

User Details:
- Conversation Details: {context}
- Goal: {goal}
{f"- Participants: {participants}" if participants else ""}
{f"- Desired Tone: {tone}" if tone else ""}

Your task is to analyze the recent conversation and provide ONE short, actionable coaching tip/prompt/guidance (max 10 words) to help them achieve their goal with the conversation. Be encouraging and specific, remembering this is streaming in real time and should help them navigate the conversation as it's happening. Make sure your advice is specific to the conversation so far and their goal for the conversation."""

        # Build user message with conversation history
        conversation_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-6:]])
        user_message = f"""Recent conversation:
{conversation_text}

What coaching tip would help {user_name} right now?"""

        response = self.openai_client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
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
        transcript: List[Dict],
        participants: str = "",
        tone: str = ""
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
- Conversation Details: {context}
- Goal: {goal}
{f"- Participants: {participants}" if participants else ""}
{f"- Desired Tone: {tone}" if tone else ""}

Full Transcript:
{transcript_text}

Analyze ONLY the user's speech (name: {user_name}). Provide:

1. Two stars (2 things they did well)
2. One wish (1 area for improvement)
3. Filler percentage (% of their words that were fillers e.g. "um", "uh", "like", "you know")
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
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert conversation coach providing feedback on a conversation the user has just had. Your goal is to encourage and help them improve their conversation skills for future conversations, bearing in mind their goal for the conversation and how it went. Only give advice helpful to the live conversation (e.g. telling them to research is not helpful as they are in the conversation currently). Always respond with valid JSON."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        return json.loads(response.choices[0].message.content)


# Global AI service instance
ai_service = AIService()
