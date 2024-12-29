import atexit
import logging
import queue
import threading
from typing import Callable, Optional, Tuple

import pyautogui

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class PyAutoGUIHandler:
    def __init__(self):
        self.task_queue: queue.Queue[Optional[Callable]] = queue.Queue()
        self.shutdown_event = threading.Event()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("PyAutoGUIHandler initialized and worker thread started.")

    def _worker(self):
        while not self.shutdown_event.is_set():
            try:
                task = self.task_queue.get(timeout=0.1)  # Allows checking for shutdown
            except queue.Empty:
                continue

            if task is None:
                logger.info("Received shutdown signal.")
                self.task_queue.task_done()
                break

            try:
                logger.debug("Executing a PyAutoGUI task.")
                task()
                logger.debug("Task executed successfully.")
            except Exception as e:
                logger.exception(f"Error executing PyAutoGUI task: {e}")
            finally:
                self.task_queue.task_done()

    def enqueue_task(self, task: Callable) -> None:
        self.task_queue.put(task)
        logger.debug("Enqueued a PyAutoGUI task.")

    def shutdown(self) -> None:
        self.shutdown_event.set()
        self.task_queue.put(None)  # Sentinel to unblock the queue and signal shutdown
        self.worker_thread.join()
        logger.info("PyAutoGUIHandler worker thread has been shut down.")

    # Utility methods to enqueue specific pyautogui actions
    def move_mouse(self, x: int, y: int, duration: float = 0.25):
        self.enqueue_task(lambda: pyautogui.moveTo(x, y, duration=duration))
        logger.info(f"Enqueued move_mouse to ({x}, {y}) over {duration}s.")

    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              button: str = "left", clicks: int = 1, interval: float = 0.0):
        self.enqueue_task(lambda: pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval))
        logger.info(f"Enqueued click: button={button}, clicks={clicks}, interval={interval}, at ({x}, {y}).")

    def type_text(self, text: str, interval: float = 0.1):
        self.enqueue_task(lambda: pyautogui.typewrite(text, interval=interval))
        logger.info(f"Enqueued type_text: '{text}' with interval {interval}s.")

    def press_key(self, key: str):
        self.enqueue_task(lambda: pyautogui.press(key))
        logger.info(f"Enqueued press_key: '{key}'.")

    def key_down(self, key: str):
        self.enqueue_task(lambda: pyautogui.keyDown(key))
        logger.info(f"Enqueued key_down: '{key}'.")

    def key_up(self, key: str):
        self.enqueue_task(lambda: pyautogui.keyUp(key))
        logger.info(f"Enqueued key_up: '{key}'.")

    def hotkey(self, *keys: str):
        self.enqueue_task(lambda: pyautogui.hotkey(*keys))
        logger.info(f"Enqueued hotkey: {keys}.")

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None):
        self.enqueue_task(lambda: pyautogui.scroll(clicks, x=x, y=y))
        logger.info(f"Enqueued scroll: clicks={clicks}, at ({x}, {y}).")

    def drag_to(self, x: int, y: int, duration: float = 0.25, button: str = "left"):
        self.enqueue_task(lambda: pyautogui.dragTo(x, y, duration=duration, button=button))
        logger.info(f"Enqueued drag_to: ({x}, {y}), duration={duration}s, button={button}.")

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Enqueue a task to get the current mouse position and wait for it to complete.
        Returns a tuple (x, y).
        """
        result_queue = queue.Queue()

        def task():
            pos = pyautogui.position()
            result_queue.put((pos.x, pos.y))
            logger.debug(f"Captured mouse position: ({pos.x}, {pos.y})")

        self.enqueue_task(task)
        # Wait for the task to complete and get the result
        try:
            return result_queue.get(timeout=2)
        except queue.Empty:
            logger.error("Failed to get mouse position within timeout.")
            return (0, 0)  # Default fallback

# Instantiate the handler
pyautogui_handler = PyAutoGUIHandler()

# Ensure graceful shutdown on application exit
@atexit.register
def shutdown_pyautogui_handler():
    pyautogui_handler.shutdown()