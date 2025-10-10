import os
import uuid
import asyncio
import json
import base64
import io
from typing import Dict
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from elevenlabs.client import ElevenLabs
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
elevenlabs_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# In-memory session store
sessions: Dict[str, dict] = {}

class SessionCreate(BaseModel):
    context: str
    goal: str
    user_name: str

class SessionResponse(BaseModel):
    session_id: str
    message: str

class FinishResponse(BaseModel):
    stars: list[str]
    wish: str
    filler_percentage: float
    takeaways: list[str]
    summary_bullets: list[str]
    transcript: list[dict]


@app.get("/")
async def root():
    return {"status": "Conversation Coach API running (OpenAI mode)"}


@app.post("/session", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "context": session_data.context,
        "goal": session_data.goal,
        "user_name": session_data.user_name,
        "transcript": [],
        "audio_buffer": b"",
        "last_suggestion_time": datetime.utcnow(),
        "conversation_history": [],
        "created_at": datetime.utcnow().isoformat(),
        "active": False
    }

    return SessionResponse(
        session_id=session_id,
        message=f"Session created. Start by saying: 'Hi, I'm {session_data.user_name}.'"
    )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live audio streaming with OpenAI"""

    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    session = sessions[session_id]
    session["active"] = True

    print(f"✅ WebSocket connected for session {session_id}")

    try:
        async def process_audio_and_generate_suggestions():
            """Background task to process audio and generate suggestions"""
            while session["active"]:
                await asyncio.sleep(3)  # Process every 3 seconds

                if len(session["audio_buffer"]) > 16000 * 2:  # At least 1 second of audio
                    print(f"🎤 Processing audio buffer ({len(session['audio_buffer'])} bytes)")

                    # Transcribe with Whisper
                    try:
                        audio_data = session["audio_buffer"]
                        session["audio_buffer"] = b""  # Clear buffer

                        # Convert PCM to WAV format for Whisper
                        import wave
                        wav_buffer = io.BytesIO()
                        with wave.open(wav_buffer, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2)  # 16-bit
                            wav_file.setframerate(16000)
                            wav_file.writeframes(audio_data)

                        wav_buffer.seek(0)
                        wav_buffer.name = "audio.wav"

                        # Transcribe
                        transcription = openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=wav_buffer,
                            language="en"
                        )

                        user_text = transcription.text.strip()

                        if user_text:
                            print(f"👤 USER: {user_text}")

                            # Add to transcript
                            session["transcript"].append({
                                "speaker": "user",
                                "text": user_text,
                                "timestamp": datetime.utcnow().isoformat()
                            })

                            # Send to frontend
                            await websocket.send_json({
                                "type": "transcript",
                                "text": user_text,
                                "speaker": "user",
                                "timestamp": datetime.utcnow().isoformat()
                            })

                            # Add to conversation history
                            session["conversation_history"].append({
                                "role": "user",
                                "content": user_text
                            })

                            # Generate coaching suggestion every ~10 seconds
                            time_since_last = (datetime.utcnow() - session["last_suggestion_time"]).seconds
                            if time_since_last >= 8 and len(session["conversation_history"]) >= 2:
                                print("💡 Generating coaching suggestion...")

                                # Generate suggestion with GPT
                                prompt = f"""You are a conversation coach helping {session['user_name']}.

Context: {session['context']}
Goal: {session['goal']}

Recent conversation:
{' '.join([f"{msg['role']}: {msg['content']}" for msg in session['conversation_history'][-6:]])}

Provide ONE short, actionable coaching tip (max 10 words) to help them achieve their goal. Be encouraging and specific."""

                                response = openai_client.chat.completions.create(
                                    model="gpt-4",
                                    messages=[
                                        {"role": "system", "content": "You are a helpful conversation coach. Give brief, actionable tips."},
                                        {"role": "user", "content": prompt}
                                    ],
                                    max_tokens=50,
                                    temperature=0.7
                                )

                                suggestion = response.choices[0].message.content.strip()
                                print(f"🤖 COACH: {suggestion}")

                                # Add to transcript
                                session["transcript"].append({
                                    "speaker": "coach",
                                    "text": suggestion,
                                    "timestamp": datetime.utcnow().isoformat()
                                })

                                # Send text to frontend
                                await websocket.send_json({
                                    "type": "suggestion",
                                    "text": suggestion,
                                    "timestamp": datetime.utcnow().isoformat()
                                })

                                # Generate TTS audio with ElevenLabs
                                try:
                                    audio_response = elevenlabs_client.text_to_speech.convert(
                                        voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice
                                        text=suggestion,
                                        model_id="eleven_turbo_v2_5"
                                    )

                                    # Collect audio bytes
                                    audio_bytes = b""
                                    for chunk in audio_response:
                                        audio_bytes += chunk

                                    # Send audio to frontend
                                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                                    await websocket.send_json({
                                        "type": "audio",
                                        "data": audio_b64,
                                        "format": "mp3"  # ElevenLabs returns MP3
                                    })

                                except Exception as e:
                                    print(f"Error generating TTS: {e}")

                                session["last_suggestion_time"] = datetime.utcnow()

                    except Exception as e:
                        print(f"❌ Error processing audio: {e}")
                        import traceback
                        traceback.print_exc()

        # Start background processing
        processing_task = asyncio.create_task(process_audio_and_generate_suggestions())

        # Main loop: receive audio from frontend
        audio_chunks_received = 0
        while session["active"]:
            try:
                data = await websocket.receive()

                if "bytes" in data:
                    # Accumulate audio in buffer
                    session["audio_buffer"] += data["bytes"]
                    audio_chunks_received += 1

                    if audio_chunks_received % 20 == 0:
                        print(f"✓ Received {audio_chunks_received} audio chunks (buffer: {len(session['audio_buffer'])} bytes)")

                elif "text" in data:
                    message = json.loads(data["text"])
                    if message.get("type") == "stop":
                        print("⏹️ Stop signal received")
                        session["active"] = False
                        break

            except WebSocketDisconnect:
                print("Client disconnected")
                session["active"] = False
                break

        # Cleanup
        processing_task.cancel()
        print("✅ WebSocket session ended")

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session["active"] = False


@app.post("/session/{session_id}/finish", response_model=FinishResponse)
async def finish_session(session_id: str):
    """End session and generate summary with AI analysis"""

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    session["active"] = False

    # Build transcript for analysis
    transcript_text = "\n".join([
        f"[{entry['timestamp']}] {entry['speaker']}: {entry['text']}"
        for entry in session["transcript"]
    ])

    if not transcript_text.strip():
        return FinishResponse(
            stars=["Started the session", "Ready to practice"],
            wish="Have a longer conversation to get more feedback",
            filler_percentage=0.0,
            takeaways=["Practice makes perfect", "Try again with a real conversation", "Focus on your goals"],
            summary_bullets=["Session started but no conversation recorded"],
            transcript=session["transcript"]
        )

    # Generate summary using OpenAI
    prompt = f"""You are analyzing a conversation coaching session.

User Details:
- Name: {session['user_name']}
- Context: {session['context']}
- Goal: {session['goal']}

Full Transcript:
{transcript_text}

Analyze ONLY the user's speech (name: {session['user_name']}). Provide:

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

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # gpt-4o supports JSON mode
            messages=[
                {"role": "system", "content": "You are a conversation coach providing feedback. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        return FinishResponse(
            stars=result["stars"],
            wish=result["wish"],
            filler_percentage=result["filler_percentage"],
            takeaways=result["takeaways"],
            summary_bullets=result["summary_bullets"],
            transcript=session["transcript"]
        )

    except Exception as e:
        print(f"Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
