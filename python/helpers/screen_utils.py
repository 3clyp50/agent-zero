import logging
import queue
from PIL import ImageDraw
import base64
from io import BytesIO

import pyautogui
from python.helpers.desktop_utils import pyautogui_handler

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def get_screenshot() -> bytes:
    """
    Capture the screenshot and draw the mouse cursor on it.
    This function enqueues tasks to move and draw, ensuring thread safety.
    """
    # Create a queue to receive the screenshot
    screenshot_queue = queue.Queue()

    def task():
        screenshot = pyautogui.screenshot()
        mouse_x, mouse_y = pyautogui.position()
        draw = ImageDraw.Draw(screenshot)

        # Define the mouse pointer shape as a polygon
        pointer_points = [
            (14.781, 5.0),
            (14.0, 6.156),
            (14.0, 39.0),
            (14.609, 39.914),
            (15.688, 39.719),
            (22.938, 32.906),
            (28.781, 46.406),
            (35.0, 43.594),
            (28.906, 30.281),
            (39.977, 28.73),
            (39.688, 27.656),
            (15.844, 5.438),
            (14.781, 5.0),
        ]

        # Scale the points to a visible size
        scale_factor = 0.75  # Adjust this value to change the size of the pointer
        scaled_points = [
            (x * scale_factor, y * scale_factor) for x, y in pointer_points
        ]

        # Translate the points to the mouse position
        translated_points = [(mouse_x + x, mouse_y + y) for x, y in scaled_points]

        # Draw the polygon
        draw.polygon(translated_points, fill="white", outline="black")

        # Convert the screenshot to RGB mode
        screenshot = screenshot.convert("RGB")

        # Save the screenshot to a bytes buffer
        buffer = BytesIO()
        screenshot.save(buffer, format="JPEG", quality=75)

        screenshot_queue.put(buffer.getvalue())
        logger.debug("Screenshot captured and processed.")

    # Enqueue the screenshot task
    pyautogui_handler.enqueue_task(task)

    # Wait for the screenshot to be processed
    try:
        return screenshot_queue.get(timeout=2)
    except queue.Empty:
        logger.error("Failed to capture screenshot within timeout.")
        return b""  # Return empty bytes on failure


def encode_screenshot(screenshot: bytes) -> str:
    return base64.b64encode(screenshot).decode("utf-8")
