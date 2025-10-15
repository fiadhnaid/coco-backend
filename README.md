# COCO - Conversation Coach Backend

Real-time AI-powered conversation coaching API built with FastAPI.

## Features

- Real-time audio transcription (OpenAI Whisper)
- Live coaching suggestions (GPT-4)
- Text-to-speech feedback (ElevenLabs)
- Session management
- Post-conversation analysis

## Quick Start

1. **Install dependencies:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Run the server:**
```bash
python main.py
```

Server runs on `http://localhost:8000`

## Project Structure

```
app/
├── api/
│   └── routes.py          # API route handlers
├── models/
│   └── session.py         # Pydantic models
├── services/
│   ├── ai_service.py      # AI operations (OpenAI, ElevenLabs)
│   └── session_manager.py # Session management
├── config.py              # Configuration
└── main.py                # FastAPI app setup
main.py                    # Entry point
requirements.txt           # Dependencies
```

## API Endpoints

### `GET /`
Health check endpoint

**Response:**
```json
{
  "status": "COCO - Conversation Coach API running (OpenAI mode)"
}
```

### `POST /session`
Create a new conversation session

**Request:**
```json
{
  "context": "Team meeting",
  "goal": "Be friendly and approachable",
  "user_name": "Alex"
}
```

**Response:**
```json
{
  "session_id": "uuid-here",
  "message": "Session created. Start by saying: 'Hi, I'm Alex.'"
}
```

### `WS /ws/{session_id}`
WebSocket endpoint for live audio streaming

**Send:** Binary PCM audio (16kHz, 16-bit, mono)

**Receive:**
```json
{
  "type": "transcript",
  "text": "...",
  "speaker": "user",
  "timestamp": "..."
}

{
  "type": "suggestion",
  "text": "...",
  "timestamp": "..."
}

{
  "type": "audio",
  "data": "base64-audio",
  "format": "mp3"
}
```

### `POST /session/{session_id}/finish`
End session and get AI-generated feedback

**Response:**
```json
{
  "stars": ["Great active listening", "Asked thoughtful questions"],
  "wish": "Reduce filler words to sound more confident",
  "filler_percentage": 5.2,
  "takeaways": ["Build on rapport", "Follow up", "Practice concise answers"],
  "summary_bullets": ["Discussed projects", "Found common interests"],
  "transcript": [...]
}
```

## Environment Variables

```env
OPENAI_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
```

## Development

The codebase follows professional Python best practices:

- **Modular architecture:** Separation of concerns (models, services, API)
- **Type hints:** Full type annotations for better IDE support
- **Clean code:** Single responsibility principle
- **Error handling:** Comprehensive error logging
- **Async/await:** Efficient concurrent operations

## Tech Stack

- **FastAPI** - Modern async web framework
- **OpenAI** - Whisper (transcription) + GPT-4 (coaching)
- **ElevenLabs** - Text-to-speech
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
