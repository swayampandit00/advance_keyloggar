import platform
import subprocess
import logging

class WindowTitleHandler:
    def __init__(self, logger):
        self.logger = logger

    def get_active_window_title(self):
        try:
            system = platform.system()
            if system == "Windows":
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                return win32gui.GetWindowText(hwnd)
            elif system == "Darwin":
                try:
                    from AppKit import NSWorkspace  # type: ignore
                    active_app = NSWorkspace.sharedWorkspace().frontmostApplication()
                    return active_app.localizedName()
                except ImportError:
                    return "Unknown"
            elif system == "Linux":
                root = subprocess.Popen(['xprop', '-root', '_NET_ACTIVE_WINDOW'], stdout=subprocess.PIPE)
                stdout, _ = root.communicate()
                window_id = stdout.decode().strip().split()[-1]
                window = subprocess.Popen(['xprop', '-id', window_id, 'WM_NAME'], stdout=subprocess.PIPE)
                stdout, _ = window.communicate()
                title = stdout.decode().strip().split('=')[-1].strip().strip('"')
                return title
            else:
                return "Unknown"
        except Exception as e:
            self.logger.error(f"Error getting active window title: {e}")
            return "Unknown"
