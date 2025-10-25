import asyncio
import os
import sys
import traceback
import pyaudio
from typing import Dict, Any, Optional, Callable

from google import genai
from dotenv import load_dotenv

load_dotenv()

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024
MODEL = "models/gemini-2.0-flash-live-001"

class AudioLoop:
    def __init__(self, system_prompt: str = None, tools: list = None, function_handler: Callable = None):
        if not os.getenv("GOOGLE_API_KEY"):
            print("Error: GOOGLE_API_KEY not found in environment variables.")
            sys.exit(1)
            
        self.client = genai.Client(http_options={"api_version": "v1beta"})
        self.pya = pyaudio.PyAudio()
        
        # Audio queues and session
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self.audio_stream = None
        
        # Function handling
        self.function_handler = function_handler
        
        # Build config
        self.config = {"response_modalities": ["AUDIO"]}
        if system_prompt:
            self.config["system_instruction"] = system_prompt
        if tools:
            self.config["tools"] = [{"function_declarations": tools}]

    async def send_audio(self):
        while True:
            audio_data = await self.out_queue.get()
            await self.session.send(input=audio_data)

    async def listen_audio(self):
        mic_info = self.pya.get_default_input_device_info()
        self.audio_stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        if __debug__:
            kwargs = {"exception_on_overflow": False}
        else:
            kwargs = {}
        while True:
            data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        while True:
            turn = self.session.receive()
            async for response in turn:
                # Handle audio data
                if data := response.data:
                    self.audio_in_queue.put_nowait(data)
                    continue
                
                # Handle text responses (for debugging)
                if text := response.text:
                    print(f"Bot: {text}")
                
                # Handle function calls
                if hasattr(response, 'function_call') and response.function_call and self.function_handler:
                    function_name = response.function_call.name
                    arguments = dict(response.function_call.args) if response.function_call.args else {}
                    
                    # Execute the function handler
                    function_result = await self.function_handler(function_name, arguments)
                    
                    # Send function result back to Gemini
                    await self.session.send(
                        input={
                            "function_response": {
                                "name": function_name,
                                "response": {"result": function_result}
                            }
                        }
                    )

            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()

    async def play_audio(self):
        stream = await asyncio.to_thread(
            self.pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        try:
            async with (
                self.client.aio.live.connect(model=MODEL, config=self.config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session

                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=5)

                tg.create_task(self.send_audio())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                await asyncio.Event().wait()

        except asyncio.CancelledError:
            pass
        except ExceptionGroup as EG:
            if hasattr(self, 'audio_stream'):
                self.audio_stream.close()
            traceback.print_exception(EG)