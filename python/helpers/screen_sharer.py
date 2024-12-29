import threading
import time
import logging
from python.helpers.screen_utils import encode_screenshot, get_screenshot

logger = logging.getLogger(__name__)


class ScreenSharer:
    def __init__(self, fps=10):
        self.fps = fps
        self.frame = None
        self.running = True
        self.lock = threading.Lock()
        threading.Thread(target=self._capture_frames, daemon=True).start()
        logger.info("ScreenSharer initialized and capture thread started.")

    def _capture_frames(self):
        while self.running:
            try:
                screenshot = get_screenshot()
                with self.lock:
                    self.frame = screenshot
                logger.debug("Frame captured and updated.")
            except Exception as e:
                logger.exception(f"Error capturing frame: {e}")
            time.sleep(1 / self.fps)

    def _get_frame_raw(self):
        with self.lock:
            return self.frame

    def get_frame(self):
        frame = self._get_frame_raw()
        if frame:
            return encode_screenshot(frame)
        return ""

    def stop(self):
        self.running = False
        logger.info("ScreenSharer stopped.")
