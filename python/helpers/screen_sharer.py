import threading
from PIL import ImageGrab
from io import BytesIO
import base64
import time


class ScreenSharer:
    def __init__(self, fps=10):
        self.fps = fps
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        threading.Thread(target=self.capture_frames, daemon=True).start()

    def capture_frames(self):
        while self.running:
            with self.lock:
                screenshot = ImageGrab.grab()
                buffer = BytesIO()
                screenshot.convert("RGB").save(buffer, format="JPEG", quality=75)
                self.frame = buffer.getvalue()
            time.sleep(1 / self.fps)

    def _get_frame_raw(self):
        with self.lock:
            return self.frame
        
    def get_frame(self):
        frame = self._get_frame_raw()
        if frame:
            return base64.b64encode(frame).decode("utf-8")

    def stop(self):
        self.running = False
