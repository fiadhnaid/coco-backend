# Conversation Coach Backend

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. **Run the server:**
```bash
python main.py
```

Server runs on `http://localhost:8000`

## API Endpoints

### 1. Create Session
**POST** `/session`

Request body:
```json
{
  "context": "I'm at a networking session at a hackathon",
  "goal": "Come across as friendly, approachable and compelling",
  "user_name": "Alex"
}
```

Response:
```json
{
  "session_id": "uuid-here",
  "message": "Session created. Start by saying: 'Hi, I'm Alex.'"
}
```

### 2. Live Audio Stream (WebSocket)
**WS** `/ws/{session_id}`

**Send to backend:**
- Audio chunks as binary data (bytes)
- Control messages as JSON: `{"type": "stop"}`

**Receive from backend:**
```json
// Suggestion text
{"type": "suggestion", "text": "Ask about their project", "timestamp": "..."}

// Suggestion audio (base64)
{"type": "audio", "data": "base64-audio-data"}

// Transcript
{"type": "transcript", "text": "...", "speaker": "user", "timestamp": "..."}

// Errors
{"type": "error", "message": "..."}
```

### 3. Finish Session
**POST** `/session/{session_id}/finish`

Response:
```json
{
  "stars": ["Great active listening", "Asked thoughtful questions"],
  "wish": "Reduce filler words to sound more confident",
  "filler_percentage": 8.5,
  "takeaways": ["Build on rapport", "Follow up on shared interests", "Practice concise answers"],
  "summary_bullets": [
    "Discussed hackathon projects",
    "Found common interest in AI/ML",
    "Exchanged contact info"
  ],
  "transcript": [
    {"speaker": "user", "text": "...", "timestamp": "..."},
    {"speaker": "coach", "text": "...", "timestamp": "..."}
  ]
}
```

## Frontend Integration

### WebSocket Client Example
```javascript
// 1. Create session
const response = await fetch('http://localhost:8000/session', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    context: "...",
    goal: "...",
    user_name: "Alex"
  })
});
const {session_id} = await response.json();

// 2. Connect WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/${session_id}`);

// 3. Handle messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'suggestion') {
    // Display suggestion text
    showSuggestion(data.text);
  } else if (data.type === 'audio') {
    // Play audio in user's ear
    playAudio(data.data);
  } else if (data.type === 'transcript') {
    // Show transcript
    addToTranscript(data.text, data.speaker);
  }
};

// 4. Send audio from microphone
navigator.mediaDevices.getUserMedia({audio: true})
  .then(stream => {
    const mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (e) => {
      ws.send(e.data);  // Send audio chunks
    };
    mediaRecorder.start(100);  // Send chunks every 100ms
  });

// 5. Stop session
ws.send(JSON.stringify({type: 'stop'}));

// 6. Get summary
const summary = await fetch(`http://localhost:8000/session/${session_id}/finish`, {
  method: 'POST'
});
const results = await summary.json();
```

## Notes

- ElevenLabs Conversational AI handles real-time coaching suggestions
- OpenAI GPT-4 analyzes the final transcript for feedback
- Sessions stored in-memory (restart clears all sessions)
- Audio format: Browser's MediaRecorder default (usually WebM/Opus)
