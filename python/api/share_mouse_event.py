from python.helpers.api import ApiHandler
from flask import Request, Response

import pyautogui
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ShareMouseEvent(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Processes mouse events and uses PyAutoGUI to replicate them.
        """

        event_type = input.get("type")
        norm_x = input.get("x")
        norm_y = input.get("y")
        button = input.get("button", "left")

        # Enhanced validation
        if event_type not in ("move", "down", "up"):
            logger.error(f"Invalid event type: {event_type}")
            return Response({"error": "Invalid mouse event type."}, status=400)

        # Validate normalized coordinates
        if not isinstance(norm_x, (int, float)) or not isinstance(norm_y, (int, float)):
            logger.error(f"Invalid coordinate types: x={norm_x}, y={norm_y}")
            return Response({"error": "Coordinates must be numbers."}, status=400)

        if not (0.0 <= norm_x <= 1.0) or not (0.0 <= norm_y <= 1.0):
            logger.error(f"Normalized coordinates out of bounds: x={norm_x}, y={norm_y}")
            return Response({"error": "Normalized coordinates must be between 0.0 and 1.0."}, status=400)

        # Validate button input
        if button not in ("left", "right", "middle"):
            logger.error(f"Invalid button type: {button}")
            return Response({"error": "Invalid mouse button type."}, status=400)

        # Get actual screen size
        screen_width, screen_height = pyautogui.size()

        # Convert normalized coordinates to actual screen coordinates
        x = int(norm_x * screen_width)
        y = int(norm_y * screen_height)

        # Validate screen boundaries after conversion
        if not (0 <= x <= screen_width) or not (0 <= y <= screen_height):
            logger.error(f"Converted coordinates out of screen bounds: ({x}, {y})")
            return Response({"error": "Converted coordinates out of screen bounds."}, status=400)

        try:
            if event_type == "move":
                logger.info(f"Moving mouse to ({x}, {y})")
                pyautogui.moveTo(x, y, duration=0.1)  # Adjust duration as needed
            elif event_type == "down":
                logger.info(f"Pressing '{button}' button at ({x}, {y})")
                pyautogui.mouseDown(x=x, y=y, button=button)
            elif event_type == "up":
                logger.info(f"Releasing '{button}' button at ({x}, {y})")
                pyautogui.mouseUp(x=x, y=y, button=button)
        except Exception as e:
            logger.exception(f"Error processing mouse event: {e}")
            return Response({"error": "Failed to process mouse event."}, status=500)

        return {
            "message": f"Mouse event '{event_type}' processed at ({x}, {y}) with button '{button}'."
        }

    def get_docstring(self) -> str:
        return """
        Mouse Events API
        Receives mouse events (move, down, up) with normalized coordinates and replicates them with PyAutoGUI.
        ---
        tags:
            -   screen
        parameters:
            -   in: body
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
