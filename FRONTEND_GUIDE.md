# Frontend Integration Guide

## Quick Test
1. Open `test_client.html` in your browser
2. Make sure backend is running: `python main.py`
3. Test the full flow!

## Integration for Your React App

### 1. API Base URL
```javascript
const API_URL = 'http://localhost:8000';
```

### 2. Create Session (Setup Screen)
```javascript
const createSession = async (userName, context, goal) => {
  const response = await fetch(`${API_URL}/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_name: userName,
      context: context,
      goal: goal
    })
  });

  const data = await response.json();
  return data.session_id; // Save this!
};
```

### 3. Start Live Session (WebSocket)
```javascript
let ws = null;
let mediaRecorder = null;

const startConversation = async (sessionId) => {
  // Connect WebSocket
  ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch(data.type) {
      case 'suggestion':
        // Display suggestion text to user
        displaySuggestion(data.text);
        break;

      case 'audio':
        // Play audio in user's ear
        playAudioBase64(data.data);
        break;

      case 'transcript':
        // Update transcript display
        addToTranscript(data.speaker, data.text);
        break;

      case 'error':
        console.error('Backend error:', data.message);
        break;
    }
  };

  // Start recording microphone
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
      ws.send(e.data); // Send audio to backend
    }
  };

  mediaRecorder.start(100); // Send chunks every 100ms
};
```

### 4. Stop Session
```javascript
const stopConversation = () => {
  if (mediaRecorder) {
    mediaRecorder.stop();
  }
  if (ws) {
    ws.send(JSON.stringify({ type: 'stop' }));
    ws.close();
  }
};
```

### 5. Get Final Feedback
```javascript
const getResults = async (sessionId) => {
  const response = await fetch(`${API_URL}/session/${sessionId}/finish`, {
    method: 'POST'
  });

  const results = await response.json();

  return {
    stars: results.stars,              // Array of 2 strings
    wish: results.wish,                // String
    fillerPercentage: results.filler_percentage,  // Number
    takeaways: results.takeaways,      // Array of 3 strings
    summary: results.summary_bullets,  // Array of 3-5 strings
    transcript: results.transcript     // Full transcript array
  };
};
```

### 6. Play Audio Helper
```javascript
const playAudioBase64 = (base64Audio) => {
  const binaryString = atob(base64Audio);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }

  const blob = new Blob([bytes], { type: 'audio/mpeg' });
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.play();
};
```

## Full Flow Example

```javascript
// 1. User fills out form
const sessionId = await createSession(
  "Alex",
  "Networking at hackathon",
  "Be friendly and compelling"
);

// 2. User clicks Start
await startConversation(sessionId);

// ... conversation happens ...
// Backend sends suggestions in real-time
// User hears audio prompts in their ear

// 3. User clicks Finish
stopConversation();

// 4. Get and display results
const results = await getResults(sessionId);
console.log('Stars:', results.stars);
console.log('Wish:', results.wish);
console.log('Filler %:', results.fillerPercentage);
```

## Important Notes

- **Audio format**: Browser MediaRecorder uses WebM by default - backend handles this
- **Real-time suggestions**: Come as both text (`suggestion` type) and audio (`audio` type)
- **Transcript**: Both user and coach speech tracked automatically
- **Error handling**: Watch for `error` type messages from WebSocket

## Testing Checklist

- [ ] Can create session
- [ ] WebSocket connects successfully
- [ ] Microphone permission granted
- [ ] Audio streaming to backend
- [ ] Suggestions appearing as text
- [ ] Audio prompts playing
- [ ] Transcript updating
- [ ] Can stop session
- [ ] Results show all fields (2 stars, wish, filler %, takeaways, summary)

## Backend API Reference

### Endpoints

**GET /** - Health check

**POST /session** - Create session
- Body: `{context, goal, user_name}`
- Returns: `{session_id, message}`

**WS /ws/{session_id}** - Live session
- Send: Binary audio chunks OR `{type: "stop"}`
- Receive: JSON messages with types: `suggestion`, `audio`, `transcript`, `error`

**POST /session/{session_id}/finish** - Get results
- Returns: `{stars, wish, filler_percentage, takeaways, summary_bullets, transcript}`
