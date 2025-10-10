import os
import uuid
import asyncio
import json
import base64
from typing import Dict
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import websockets
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

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ElevenLabs config
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
AGENT_ID = "agent_2801k776e9gmfm9vrnez35fzhrd6"
ELEVENLABS_WS_URL = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"

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
    return {"status": "Conversation Coach API running"}


@app.post("/session", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """Create a new conversation session"""
    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "context": session_data.context,
        "goal": session_data.goal,
        "user_name": session_data.user_name,
        "transcript": [],
        "created_at": datetime.utcnow().isoformat(),
        "active": False
    }

    return SessionResponse(
        session_id=session_id,
        message=f"Session created. Start by saying: 'Hi, I'm {session_data.user_name}.'"
    )


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for live audio streaming with ElevenLabs Conversational AI"""

    if session_id not in sessions:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    session = sessions[session_id]
    session["active"] = True

    elevenlabs_ws = None

    try:
        # Connect to ElevenLabs WebSocket with agent
        elevenlabs_ws = await websockets.connect(
            ELEVENLABS_WS_URL,
            additional_headers={
                "xi-api-key": ELEVENLABS_API_KEY
            }
        )

        print(f"Connected to ElevenLabs for session {session_id}")

        # Task to forward client audio to ElevenLabs
        async def forward_to_elevenlabs():
            try:
                audio_chunks_sent = 0
                while session["active"]:
                    data = await websocket.receive()

                    if "bytes" in data:
                        # Forward PCM audio chunk to ElevenLabs (already in correct format)
                        audio_b64 = base64.b64encode(data["bytes"]).decode('utf-8')
                        audio_message = {
                            "user_audio_chunk": audio_b64
                        }
                        await elevenlabs_ws.send(json.dumps(audio_message))
                        audio_chunks_sent += 1
                        if audio_chunks_sent % 10 == 0:
                            print(f"✓ Sent {audio_chunks_sent} audio chunks to ElevenLabs")

                    elif "text" in data:
                        message = json.loads(data["text"])
                        print(f"Received control message: {message}")
                        if message.get("type") == "stop":
                            session["active"] = False
                            break

            except WebSocketDisconnect:
                print("Client disconnected")
                session["active"] = False
            except Exception as e:
                print(f"❌ Error forwarding to ElevenLabs: {e}")
                import traceback
                traceback.print_exc()
                session["active"] = False

        # Task to receive responses from ElevenLabs
        async def receive_from_elevenlabs():
            try:
                async for message in elevenlabs_ws:
                    if not session["active"]:
                        break

                    try:
                        data = json.loads(message)
                        print(f"Received from ElevenLabs: {data.get('type', 'unknown')}")

                        # Handle different event types
                        event_type = data.get("type")

                        # Audio event
                        if event_type == "audio" and "audio_event" in data:
                            audio_b64 = data["audio_event"].get("audio_base_64")
                            if audio_b64:
                                await websocket.send_json({
                                    "type": "audio",
                                    "data": audio_b64
                                })

                        # User transcript
                        elif event_type == "user_transcript":
                            text = data.get("user_transcript", {}).get("text", "")
                            if text:
                                print(f"👤 USER: {text}")
                                session["transcript"].append({
                                    "speaker": "user",
                                    "text": text,
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                await websocket.send_json({
                                    "type": "transcript",
                                    "text": text,
                                    "speaker": "user",
                                    "timestamp": datetime.utcnow().isoformat()
                                })

                        # Agent response (text)
                        elif event_type == "agent_response":
                            text = data.get("agent_response", {}).get("text", "")
                            if text:
                                print(f"🤖 COACH: {text}")
                                session["transcript"].append({
                                    "speaker": "coach",
                                    "text": text,
                                    "timestamp": datetime.utcnow().isoformat()
                                })
                                await websocket.send_json({
                                    "type": "suggestion",
                                    "text": text,
                                    "timestamp": datetime.utcnow().isoformat()
                                })

                        # Ping - respond with pong
                        elif event_type == "ping":
                            event_id = data.get("ping_event", {}).get("event_id", 0)
                            await elevenlabs_ws.send(json.dumps({
                                "type": "pong",
                                "event_id": event_id
                            }))

                        # Interruption
                        elif event_type == "interruption":
                            print("User interruption detected")

                        # Log unknown types for debugging
                        else:
                            print(f"Unknown event type: {event_type}, data: {data}")

                    except json.JSONDecodeError:
                        # Binary audio data, skip
                        pass

            except Exception as e:
                print(f"Error receiving from ElevenLabs: {e}")
                import traceback
                traceback.print_exc()
                session["active"] = False

        # Run both tasks concurrently
        await asyncio.gather(
            forward_to_elevenlabs(),
            receive_from_elevenlabs()
        )

    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

    finally:
        session["active"] = False
        if elevenlabs_ws:
            await elevenlabs_ws.close()


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
        # No conversation happened, return defaults
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a conversation coach providing feedback."},
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
