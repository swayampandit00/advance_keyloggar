import threading
import datetime
import wave
import sounddevice as sd
import asyncio
import logging

class AudioRecorder:
    def __init__(self, audio_interval, logger, api_token=None, chat_id=None, telegram_handler=None, loop=None):
        self.audio_interval = audio_interval
        self.logger = logger
        self.api_token = api_token
        self.chat_id = chat_id
        self.telegram_handler = telegram_handler
        self.loop = loop
        self.stop_event = threading.Event()
        self.audio_thread = None

    def audio_recording_monitor(self):
        while not self.stop_event.is_set():
            try:
                duration = self.audio_interval
                fs = 44100  # Sample rate
                self.logger.info(f"Starting audio recording for {duration} seconds...")
                recording = sd.rec(int(duration * fs), samplerate=fs, channels=2, dtype='int16')
                sd.wait()  # Wait until recording is finished
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"audio_recording_{timestamp}.wav"
                # Save recording to WAV file
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(2)
                    wf.setsampwidth(2)  # 16 bits = 2 bytes
                    wf.setframerate(fs)
                    wf.writeframes(recording.tobytes())
                self.logger.info(f"Audio recording saved: {filename}")
                # Send audio file via Telegram if enabled
                if self.telegram_handler and self.api_token and self.chat_id:
                    self.loop.call_soon_threadsafe(asyncio.ensure_future, self.telegram_handler.send_audio_to_telegram(filename))
            except Exception as e:
                self.logger.error(f"Error during audio recording: {e}")

    def start_audio_monitor(self):
        self.audio_thread = threading.Thread(target=self.audio_recording_monitor, daemon=True)
        self.audio_thread.start()

    def stop_audio_monitor(self):
        self.stop_event.set()
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join()
