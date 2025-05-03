import os
import base64
import hashlib
from cryptography.fernet import Fernet
import logging

MAX_LOG_FILE_SIZE = 1024 * 1024  # 1MB max log file size for rotation

def generate_key(password=b"my_secret_password"):
    key = hashlib.sha256(password).digest()
    return base64.urlsafe_b64encode(key)

def rotate_log_file_if_needed(log_file, logger):
    try:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            if size >= MAX_LOG_FILE_SIZE:
                backup_file = log_file + ".bak"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(log_file, backup_file)
                logger.info(f"Log file rotated: {log_file} -> {backup_file}")
    except Exception as e:
        logger.error(f"Error rotating log file: {e}")

def encrypt_and_save(data, cipher, log_file, logger):
    try:
        rotate_log_file_if_needed(log_file, logger)
        encrypted = cipher.encrypt(data.encode())
        with open(log_file, "ab") as f:
            f.write(encrypted + b"\n")
    except Exception as e:
        logger.error(f"Error saving encrypted log: {e}")
