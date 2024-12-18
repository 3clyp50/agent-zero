import threading
import time

from python.helpers.screen_utils import encode_screenshot, get_screenshot

class ScreenSharer:
    def __init__(self, fps=10):
        self.fps = fps
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        threading.Thread(target=self._capture_frames, daemon=True).start()

    def _capture_frames(self):
        while self.running:
            with self.lock:
                self.frame = get_screenshot()
            time.sleep(1 / self.fps)

    def _get_frame_raw(self):
        with self.lock:
            return self.frame
        
    def get_frame(self):
        frame = self._get_frame_raw()
        if frame:
            return encode_screenshot(self.frame)

    def stop(self):
        self.running = False
