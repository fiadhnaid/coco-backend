import asyncio
import json
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from app.models.session import SessionCreate, SessionResponse, FinishResponse
from app.services.session_manager import session_manager
from app.services.ai_service import ai_service


async def create_session(session_data: SessionCreate) -> SessionResponse:
    """Create a new conversation session"""
    session_id = session_manager.create_session(
        context=session_data.context,
        goal=session_data.goal,
        user_name=session_data.user_name
    )

    return SessionResponse(
        session_id=session_id,
        message=f"Session created. Start by saying: 'Hi, I'm {session_data.user_name}.'"
    )


async def websocket_handler(websocket: WebSocket, session_id: str):
    """Handle WebSocket connection for real-time audio streaming"""
    if not session_manager.session_exists(session_id):
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    session = session_manager.get_session(session_id)
    session.active = True

    print(f"✅ WebSocket connected for session {session_id}")

    try:
        async def process_audio_and_generate_suggestions():
            """Background task to process audio and generate suggestions"""
            while session.active:
                await asyncio.sleep(3)  # Process every 3 seconds

                if len(session.audio_buffer) > 16000 * 2:  # At least 1 second of audio
                    print(f"🎤 Processing audio buffer ({len(session.audio_buffer)} bytes)")

                    try:
                        audio_data = session.audio_buffer
                        session.audio_buffer = b""  # Clear buffer

                        # Transcribe with Whisper
                        user_text = ai_service.transcribe_audio(audio_data)

                        if user_text:
                            print(f"👤 USER: {user_text}")

                            # Add to transcript
                            entry = session.add_transcript_entry("user", user_text)

                            # Send to frontend
                            await websocket.send_json({
                                "type": "transcript",
                                "text": user_text,
                                "speaker": "user",
                                "timestamp": entry["timestamp"]
                            })

                            # Add to conversation history
                            session.conversation_history.append({
                                "role": "user",
                                "content": user_text
                            })

                            # Generate coaching suggestion every ~10 seconds
                            time_since_last = (datetime.utcnow() - session.last_suggestion_time).seconds
                            if time_since_last >= 8 and len(session.conversation_history) >= 2:
                                print("💡 Generating coaching suggestion...")

                                # Generate suggestion with GPT
                                suggestion = ai_service.generate_coaching_suggestion(
                                    user_name=session.user_name,
                                    context=session.context,
                                    goal=session.goal,
                                    conversation_history=session.conversation_history
                                )

                                print(f"🤖 COACH: {suggestion}")

                                # Add to transcript
                                session.add_transcript_entry("coach", suggestion)

                                # Send text to frontend
                                await websocket.send_json({
                                    "type": "suggestion",
                                    "text": suggestion,
                                    "timestamp": datetime.utcnow().isoformat()
                                })

                                # Generate TTS audio with ElevenLabs
                                try:
                                    audio_b64 = ai_service.generate_tts_audio(suggestion)
                                    await websocket.send_json({
                                        "type": "audio",
                                        "data": audio_b64,
                                        "format": "mp3"
                                    })
                                except Exception as e:
                                    print(f"Error generating TTS: {e}")

                                session.last_suggestion_time = datetime.utcnow()

                    except Exception as e:
                        print(f"❌ Error processing audio: {e}")
                        import traceback
                        traceback.print_exc()

        # Start background processing
        processing_task = asyncio.create_task(process_audio_and_generate_suggestions())

        # Main loop: receive audio from frontend
        audio_chunks_received = 0
        while session.active:
            try:
                data = await websocket.receive()

                if "bytes" in data:
                    # Accumulate audio in buffer
                    session.audio_buffer += data["bytes"]
                    audio_chunks_received += 1

                    if audio_chunks_received % 20 == 0:
                        print(f"✓ Received {audio_chunks_received} audio chunks (buffer: {len(session.audio_buffer)} bytes)")

                elif "text" in data:
                    message = json.loads(data["text"])
                    if message.get("type") == "stop":
                        print("⏹️ Stop signal received")
                        session.active = False
                        break

            except WebSocketDisconnect:
                print("Client disconnected")
                session.active = False
                break

        # Cleanup
        processing_task.cancel()
        print("✅ WebSocket session ended")

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.active = False


async def finish_session(session_id: str) -> FinishResponse:
    """End session and generate summary with AI analysis"""
    if not session_manager.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    session = session_manager.get_session(session_id)
    session.active = False

    # Analyze session using AI
    result = ai_service.analyze_session(
        user_name=session.user_name,
        context=session.context,
        goal=session.goal,
        transcript=session.transcript
    )

    return FinishResponse(
        stars=result["stars"],
        wish=result["wish"],
        filler_percentage=result["filler_percentage"],
        takeaways=result["takeaways"],
        summary_bullets=result["summary_bullets"],
        transcript=session.transcript
    )
