from python.helpers.api import ApiHandler
from flask import Request, Response

import pyautogui
import asyncio
import logging
import threading

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize a global threading lock for synchronizing pyautogui access
mouse_lock = threading.Lock()

class ShareMouseEvent(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Processes mouse events and uses PyAutoGUI to replicate them.
        """

        logger.info(f"Received input: {input}")

        event_type = input.get("type")
        x = input.get("x")
        y = input.get("y")
        button = input.get("button", "left")

        logger.info(f"Event Type: {event_type}, X: {x}, Y: {y}, Button: {button}")

        # Enhanced validation
        if event_type not in ("move", "down", "up"):
            logger.error(f"Invalid event type: {event_type}")
            return Response({"error": "Invalid mouse event type."}, status=400)

        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            logger.error(f"Invalid coordinates: x={x}, y={y}")
            return Response({"error": "Invalid coordinates for mouse event."}, status=400)

        # Validate button input
        if button not in ("left", "right", "middle"):
            logger.error(f"Invalid button type: {button}")
            return Response({"error": "Invalid mouse button type."}, status=400)

        # Validate screen boundaries
        screen_width, screen_height = pyautogui.size()
        if not (0 <= x <= screen_width) or not (0 <= y <= screen_height):
            logger.error(f"Coordinates out of screen bounds: ({x}, {y})")
            return Response({"error": "Coordinates out of screen bounds."}, status=400)

        # Define the function to execute pyautogui commands
        def execute_mouse_event():
            with mouse_lock:
                if event_type == "move":
                    logger.info(f"Moving mouse to ({x}, {y})")
                    pyautogui.moveTo(x, y, duration=0.1)  # Adjust duration as needed
                elif event_type == "down":
                    logger.info(f"Pressing '{button}' button at ({x}, {y})")
                    pyautogui.mouseDown(x=x, y=y, button=button)
                elif event_type == "up":
                    logger.info(f"Releasing '{button}' button at ({x}, {y})")
                    pyautogui.mouseUp(x=x, y=y, button=button)

        try:
            # Run the synchronous mouse event in a separate thread to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, execute_mouse_event)
        except Exception as e:
            logger.exception(f"Error processing mouse event: {e}")
            return Response({"error": "Failed to process mouse event."}, status=500)

        return {
            "message": f"Mouse event '{event_type}' processed at ({x}, {y}) with button '{button}'."
        }

    def get_docstring(self) -> str:
        return """
        Mouse Events API
        Receives mouse events (move, down, up) and replicates them with PyAutoGUI.
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
                            description: The x-coordinate for the event.
                        y:
                            type: number
                            description: The y-coordinate for the event.
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
