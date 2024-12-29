import logging
import queue
from enum import Enum
from typing import Any, Dict

from flask import Request, Response
import pyautogui
from python.helpers.api import ApiHandler
from python.helpers.desktop_utils import pyautogui_handler


# Define Enums for Mouse Event Types and Buttons
class MouseEventType(Enum):
    MOVE = "move"
    DOWN = "down"
    UP = "up"


class MouseButton(Enum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class MouseEventHandler:
    def __init__(self) -> None:
        logger.info("MouseEventHandler initialized.")

    def enqueue_event(
        self, event_type: MouseEventType, x: int, y: int, button: MouseButton
    ) -> None:
        if event_type == MouseEventType.MOVE:
            pyautogui_handler.move_mouse(x, y, duration=0.1)
        elif event_type == MouseEventType.DOWN:
            pyautogui_handler.click(
                x=x, y=y, button=button.value, clicks=1, interval=0.0
            )
            # Alternatively, use mouseDown if needed
            # pyautogui_handler.enqueue_task(lambda: pyautogui.mouseDown(x=x, y=y, button=button.value))
        elif event_type == MouseEventType.UP:
            pyautogui_handler.click(
                x=x, y=y, button=button.value, clicks=1, interval=0.0
            )
            # Alternatively, use mouseUp if needed
            # pyautogui_handler.enqueue_task(lambda: pyautogui.mouseUp(x=x, y=y, button=button.value))
        logger.info(
            f"Enqueued mouse event '{event_type.value}' at ({x}, {y}) with button '{button.value}'."
        )


# Instantiate the MouseEventHandler
mouse_event_handler = MouseEventHandler()


class ShareMouseEvent(ApiHandler):
    async def process(self, input: Dict[str, Any], request: Request) -> Response:
        """
        Processes mouse events and uses PyAutoGUI to replicate them.
        """
        # Extract and validate input
        try:
            event_type_str: str = input["type"]
            norm_x: float = input["x"]
            norm_y: float = input["y"]
            button_str: str = input.get("button", "left")
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            return Response(
                {"error": f"Missing required field: {e}"},
                status=400,
                mimetype="application/json",
            )
        except (TypeError, ValueError) as e:
            logger.error(f"Invalid input data: {e}")
            return Response(
                {"error": "Invalid input data."},
                status=400,
                mimetype="application/json",
            )

        # Validate event type
        try:
            event_type = MouseEventType(event_type_str)
        except ValueError:
            logger.error(f"Invalid event type: {event_type_str}")
            return Response(
                {"error": "Invalid mouse event type."},
                status=400,
                mimetype="application/json",
            )

        # Validate normalized coordinates
        if not (0.0 <= norm_x <= 1.0) or not (0.0 <= norm_y <= 1.0):
            logger.error(
                f"Normalized coordinates out of bounds: x={norm_x}, y={norm_y}"
            )
            return Response(
                {"error": "Normalized coordinates must be between 0.0 and 1.0."},
                status=400,
                mimetype="application/json",
            )

        # Validate button
        try:
            button = MouseButton(button_str)
        except ValueError:
            logger.error(f"Invalid button type: {button_str}")
            return Response(
                {"error": "Invalid mouse button type."},
                status=400,
                mimetype="application/json",
            )

        # Get actual screen size
        screen_width, screen_height = (
            pyautogui_handler.get_mouse_position()
        )

        screen_size_queue = queue.Queue()
        pyautogui_handler.enqueue_task(lambda: screen_size_queue.put(pyautogui.size()))
        try:
            screen_width, screen_height = screen_size_queue.get(timeout=2)
        except queue.Empty:
            logger.error("Failed to get screen size within timeout.")
            return Response(
                {"error": "Internal server error."},
                status=500,
                mimetype="application/json",
            )

        logger.debug(f"Screen size: width={screen_width}, height={screen_height}")

        # Convert normalized coordinates to actual screen coordinates
        x = int(norm_x * screen_width)
        y = int(norm_y * screen_height)
        logger.debug(f"Converted coordinates: x={x}, y={y}")

        # Validate screen boundaries after conversion
        if not (0 <= x < screen_width) or not (0 <= y < screen_height):
            logger.error(f"Converted coordinates out of screen bounds: ({x}, {y})")
            return Response(
                {"error": "Converted coordinates out of screen bounds."},
                status=400,
                mimetype="application/json",
            )

        # Enqueue the mouse event
        mouse_event_handler.enqueue_event(event_type, x, y, button)

        return Response(
            {"message": "Mouse event enqueued successfully."},
            status=200,
            mimetype="application/json",
        )

    def get_docstring(self) -> str:
        return """
        Mouse Events API
        Receives mouse events (move, down, up) with normalized coordinates and replicates them with PyAutoGUI.
        ---
        tags:
            - screen
        parameters:
            - in: body
              name: body
              required: true
              schema:
                  id: ShareMouseEventRequest
                  required:
                      - type
                      - x
                      - y
                  properties:
                      type:
                          type: string
                          description: The mouse event type ("move", "down", "up").
                      x:
                          type: number
                          format: float
                          minimum: 0.0
                          maximum: 1.0
                          description: The normalized x-coordinate for the event (0.0 to 1.0).
                      y:
                          type: number
                          format: float
                          minimum: 0.0
                          maximum: 1.0
                          description: The normalized y-coordinate for the event (0.0 to 1.0).
                      button:
                          type: string
                          description: Which mouse button ("left", "right", "middle").
        responses:
            200:
                description: Successfully processed mouse event.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Confirmation of event processing.
            400:
                description: Missing or invalid mouse event data.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message.
            500:
                description: Internal server error.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
