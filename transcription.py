# transcription.py — CLEAN + WORKING (NO SPAM)

import os
from dotenv import load_dotenv
load_dotenv()

import speechmatics
import sounddevice as sd
import threading
from queue import Queue

API_KEY = os.getenv("SPEECHMATICS_API_KEY")
LANGUAGE = "en"
CONNECTION_URL = "wss://eu2.rt.speechmatics.com/v2"

SAMPLE_RATE = 16000
BLOCK_SIZE = 8000


class MicrophoneStream:
    def __init__(self):
        self.running = True
        self.q = Queue()

        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=self.callback,
        )
        self.stream.start()

    def callback(self, indata, frames, time, status):
        if self.running:
            self.q.put(bytes(indata))

    def read(self, chunk_size):
        if not self.running:
            return b""
        try:
            return self.q.get(timeout=1)
        except:
            return b""

    def stop(self):
        self.running = False

    def close(self):
        try:
            self.stream.stop()
            self.stream.close()
        except:
            pass


class TranscriptionManager:
    def __init__(self):
        self.transcript_parts = []
        self.thread = None
        self.ws_client = None
        self.mic = None
        self.is_running = False
        self._lock = threading.Lock()

    def _handle_partial(self, msg):
        text = msg["metadata"]["transcript"]
        with self._lock:
            if self.transcript_parts:
                self.transcript_parts[-1] = text
            else:
                self.transcript_parts.append(text)

    def _handle_full(self, msg):
        text = msg["metadata"]["transcript"]
        with self._lock:
            self.transcript_parts.append(text)

    def _worker(self):
        try:
            settings = speechmatics.models.ConnectionSettings(
                url=CONNECTION_URL,
                auth_token=API_KEY,
            )

            self.ws_client = speechmatics.client.WebsocketClient(settings)

            self.ws_client.add_event_handler(
                speechmatics.models.ServerMessageType.AddPartialTranscript,
                self._handle_partial,
            )
            self.ws_client.add_event_handler(
                speechmatics.models.ServerMessageType.AddTranscript,
                self._handle_full,
            )

            audio_settings = speechmatics.models.AudioSettings(
                encoding="pcm_s16le",
                sample_rate=SAMPLE_RATE,
                chunk_size=BLOCK_SIZE,
            )

            config = speechmatics.models.TranscriptionConfig(
                language=LANGUAGE,
                enable_partials=True,
                operating_point="enhanced",
            )

            self.mic = MicrophoneStream()
            self.ws_client.run_synchronously(self.mic, config, audio_settings)

        except Exception as e:
            print("❌ Transcription Error:", e)

        finally:
            if self.mic:
                self.mic.close()
            print("⚠️ Transcription Stopped")

    def start_streaming(self):
        if self.is_running:
            return
        self.is_running = True
        self.transcript_parts = []
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def stop_streaming(self):
        if not self.is_running:
            return self.transcript_parts

        self.is_running = False

        if self.mic:
            self.mic.stop()
        if self.ws_client:
            try:
                self.ws_client.stop()
            except:
                pass
        if self.thread:
            self.thread.join(timeout=2)

        return self.transcript_parts.copy()

    def get_transcript(self):
        return self.transcript_parts.copy()
