import asyncio
import logging

class TelegramHandler:
    def __init__(self, api_token, chat_id, logger):
        self.api_token = api_token
        self.chat_id = chat_id
        self.logger = logger
        self.telegram_available = self.check_telegram_availability()

    def check_telegram_availability(self):
        try:
            import telegram
            return True
        except ImportError:
            self.logger.warning("Telegram library not found. Telegram sending disabled.")
            return False

    async def send_to_telegram(self, message):
        if not self.api_token or not self.chat_id or not self.telegram_available:
            return
        try:
            from telegram import Bot
            from telegram.constants import ParseMode
            bot = Bot(self.api_token)
            await bot.send_message(chat_id=self.chat_id, text=message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            self.logger.error(f"Error sending message to Telegram: {e}")

    async def send_image_to_telegram(self, image_path):
        if not self.api_token or not self.chat_id or not self.telegram_available:
            return
        try:
            from telegram import Bot
            bot = Bot(self.api_token)
            with open(image_path, "rb") as f:
                await bot.send_photo(chat_id=self.chat_id, photo=f)
        except Exception as e:
            self.logger.error(f"Error sending image to Telegram: {e}")

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
