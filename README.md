# Voice Bot with Gemini Live API

A Flask web application that provides voice interaction with Google's Gemini Live API.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Add your Google API key to the `.env` file:
     ```
     GOOGLE_API_KEY=your_google_api_key_here
     ```

3. **Important: Use headphones!** 
   This prevents audio feedback between the microphone and speakers.

## Running the Application

### Option 1: Using the run script (recommended)
```bash
python run.py
```

### Option 2: Direct Flask run
```bash
python app.py
```

## Usage

1. Open your browser to `http://localhost:5000`
2. **Put on headphones** (very important!)
3. Click the red microphone button to start voice conversation
4. Speak naturally - the AI will respond with both text and audio
5. Click the microphone button again to stop listening

## Features

- **Audio-only mode**: No camera or screen sharing, just voice
- **Real-time conversation**: Immediate audio responses
- **Web interface**: Easy-to-use browser interface
- **Live transcription**: See what you said and the AI's responses
- **WebSocket communication**: Real-time updates

## Technical Details

- Built with Flask and Flask-SocketIO
- Integrates with Google's Gemini 2.0 Flash Live API
- Uses PyAudio for microphone and speaker access
- Real-time audio streaming with WebSocket

## Troubleshooting

- **No microphone access**: Check browser permissions
- **Audio feedback**: Make sure you're using headphones
- **Connection issues**: Verify your Google API key is correct
- **Audio quality**: Ensure your microphone is working properly