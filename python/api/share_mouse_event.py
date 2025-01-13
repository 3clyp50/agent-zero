import logging
import queue
from enum import Enum
from typing import Any, Dict, Tuple

from flask import Request, Response
import pyautogui
from python.helpers.api import ApiHandler
from python.helpers.desktop_utils import pyautogui_handler
from python.tools.vision import analyze_screen  # Import the vision analysis function
from python.helpers.screen_utils import save_screenshot


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
        self, event_type: MouseEventType, coordinates: Tuple[int, int], button: MouseButton
    ) -> None:
        x, y = coordinates
        if event_type == MouseEventType.MOVE:
            pyautogui_handler.move_mouse(x, y, duration=0.0)
        elif event_type == MouseEventType.DOWN:
            pyautogui_handler.mouse_down(x=x, y=y, button=button.value)
        elif event_type == MouseEventType.UP:
            pyautogui_handler.mouse_up(x=x, y=y, button=button.value)
        logger.info(
            f"Enqueued mouse event '{event_type.value}' at ({x}, {y}) with button '{button.value}'."
        )


# Instantiate the MouseEventHandler
mouse_event_handler = MouseEventHandler()


class ShareMouseEvent(ApiHandler):
    async def process(self, input: Dict[str, Any], request: Request) -> Response:
        """
        Processes mouse events by first analyzing the screen to get exact coordinates using Atlas,
        then enqueues the mouse event with those coordinates.
        """
        # Extract and validate input
        try:
            event_type_str: str = input["type"]
            button_str: str = input.get("button", "left")
            element_description: str = input["element_description"]
            logger.info(f"Processing mouse event: type={event_type_str}, button={button_str}, description='{element_description}'")
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

        # Analyze screen to get exact coordinates
        logger.info("Getting coordinates from Atlas...")
        coordinates = analyze_screen(None, element_description)  # Pass None to let vision tool handle screenshot
        if not coordinates:
            logger.error("Atlas failed to provide coordinates")
            return Response(
                {"error": "Failed to locate the UI element."},
                status=400,
                mimetype="application/json",
            )
        
        logger.info(f"Received coordinates from Atlas: {coordinates}")

        # Retrieve button enum
        try:
            button = MouseButton(button_str)
        except ValueError:
            logger.error(f"Invalid button type: {button_str}")
            return Response(
                {"error": "Invalid mouse button type."},
                status=400,
                mimetype="application/json",
            )

        # Log the final event details
        logger.info(f"Enqueueing mouse event: type={event_type.value}, coordinates={coordinates}, button={button.value}")
        
        # Enqueue the mouse event with exact coordinates
        mouse_event_handler.enqueue_event(event_type, coordinates, button)

        return Response(
            {"message": f"Mouse event enqueued successfully at coordinates {coordinates}"},
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
