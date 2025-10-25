from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import asyncio
import threading
import base64
import pyaudio
from datetime import datetime
import os
from google import genai
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if sys.version_info < (3, 11, 0):
    import taskgroup, exceptiongroup
    asyncio.TaskGroup = taskgroup.TaskGroup
    asyncio.ExceptionGroup = exceptiongroup.ExceptionGroup

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

MODEL = "models/gemini-2.0-flash-live-001"
CONFIG = {"response_modalities": ["AUDIO"]}

# Initialize Google AI client
client = genai.Client(http_options={"api_version": "v1beta"})
pya = pyaudio.PyAudio()

class VoiceBot:
    def __init__(self):
        self.session = None
        self.audio_in_queue = None
        self.out_queue = None
        self.audio_stream = None
        self.is_listening = False
        self.tasks = []
        
    async def start_session(self):
        """Start the Live API session"""
        try:
            self.session = await client.aio.live.connect(model=MODEL, config=CONFIG).__aenter__()
            self.audio_in_queue = asyncio.Queue()
            self.out_queue = asyncio.Queue(maxsize=5)
            
            # Start background tasks
            self.tasks = [
                asyncio.create_task(self.send_realtime()),
                asyncio.create_task(self.receive_audio()),
                asyncio.create_task(self.play_audio())
            ]
            
            socketio.emit('status', {'message': 'Connected to Gemini Live API'})
            return True
        except Exception as e:
            socketio.emit('status', {'message': f'Failed to connect: {str(e)}'})
            return False
    
    async def stop_session(self):
        """Stop the Live API session"""
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            
        for task in self.tasks:
            task.cancel()
            
        if self.session:
            await self.session.__aexit__(None, None, None)
            
        self.is_listening = False
        socketio.emit('status', {'message': 'Disconnected'})
    
    async def start_listening(self):
        """Start listening to microphone"""
        if self.is_listening:
            return
            
        try:
            mic_info = pya.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            self.is_listening = True
            self.tasks.append(asyncio.create_task(self.listen_audio()))
            socketio.emit('status', {'message': 'Listening...'})
            
        except Exception as e:
            socketio.emit('status', {'message': f'Microphone error: {str(e)}'})
    
    async def stop_listening(self):
        """Stop listening to microphone"""
        self.is_listening = False
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        socketio.emit('status', {'message': 'Stopped listening'})
    
    async def listen_audio(self):
        """Listen to audio from microphone and send to API"""
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        
        while self.is_listening:
            try:
                data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
            except Exception as e:
                print(f"Audio listening error: {e}")
                break
    
    async def send_realtime(self):
        """Send audio data to the Live API"""
        while True:
            try:
                msg = await self.out_queue.get()
                if self.session:
                    await self.session.send(input=msg)
            except Exception as e:
                print(f"Send error: {e}")
                break
    
    async def receive_audio(self):
        """Receive audio responses from the Live API"""
        while True:
            try:
                if not self.session:
                    break
                    
                turn = self.session.receive()
                async for response in turn:
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                        continue
                    if text := response.text:
                        # Emit the bot's text response to frontend
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        socketio.emit('bot_response', {
                            'text': text, 
                            'timestamp': timestamp
                        })
                
                # Clear audio queue on interruption
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()
                    
            except Exception as e:
                print(f"Receive error: {e}")
                break
    
    async def play_audio(self):
        """Play audio responses"""
        try:
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            
            while True:
                bytestream = await self.audio_in_queue.get()
                await asyncio.to_thread(stream.write, bytestream)
                
        except Exception as e:
            print(f"Audio playback error: {e}")

# Global voice bot instance
voice_bot = VoiceBot()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'message': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('start_voice')
def handle_start_voice():
    """Handle start voice command from frontend"""
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def start_voice_session():
            # Start session if not already started
            if not voice_bot.session:
                success = await voice_bot.start_session()
                if not success:
                    return
            
            # Start listening
            await voice_bot.start_listening()
        
        loop.run_until_complete(start_voice_session())
    
    thread = threading.Thread(target=run_async)
    thread.daemon = True
    thread.start()

@socketio.on('stop_voice')
def handle_stop_voice():
    """Handle stop voice command from frontend"""
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(voice_bot.stop_listening())
    
    thread = threading.Thread(target=run_async)
    thread.daemon = True
    thread.start()

@socketio.on('simulate_voice_input')
def handle_simulate_voice():
    """Simulate voice input for testing"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emit('user_input', {'text': 'Hello, I would like to order some food', 'timestamp': timestamp})
    emit('bot_response', {'text': 'Hello! I\'d be happy to help you with your food order. What would you like to eat today?', 'timestamp': timestamp})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)