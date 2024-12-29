import logging
from enum import Enum
from typing import Any, Dict

from flask import Request, Response
from python.helpers.api import ApiHandler
from python.helpers.desktop_utils import pyautogui_handler


# Define Enums for Keyboard Event Types (Optional but recommended for validation)
class KeyboardEventType(Enum):
    KEYDOWN = "keydown"
    KEYUP = "keyup"


# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


class ShareKeyboardEvent(ApiHandler):
    async def process(self, input: Dict[str, Any], request: Request) -> Response:
        """
        Processes keyboard events and uses PyAutoGUIHandler to replicate them.
        """
        # Extract and validate input
        try:
            event_type_str: str = input["type"]
            key: str = input["key"]
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
            event_type = KeyboardEventType(event_type_str)
        except ValueError:
            logger.error(f"Invalid event type: {event_type_str}")
            return Response(
                {"error": "Invalid keyboard event type."},
                status=400,
                mimetype="application/json",
            )

        # Additional validation for key can be added here if necessary
        if not isinstance(key, str) or not key:
            logger.error(f"Invalid key: {key}")
            return Response(
                {"error": "Invalid key provided."},
                status=400,
                mimetype="application/json",
            )

        # Enqueue the keyboard event
        if event_type == KeyboardEventType.KEYDOWN:
            pyautogui_handler.key_down(key)
            logger.info(f"Enqueued keyboard event 'keydown' for key '{key}'.")
        elif event_type == KeyboardEventType.KEYUP:
            pyautogui_handler.key_up(key)
            logger.info(f"Enqueued keyboard event 'keyup' for key '{key}'.")

        return Response(
            {
                "message": f"Keyboard event '{event_type.value}' enqueued for key '{key}'."
            },
            status=200,
            mimetype="application/json",
        )

    def get_docstring(self) -> str:
        return """
        Keyboard Events API
        Receives keyboard events (keydown, keyup) and replicates them with PyAutoGUIHandler.
        ---
        tags:
            - screen
        parameters:
            - in: body
              name: body
              required: true
              schema:
                  id: ShareKeyboardEventRequest
                  required:
                      - type
                      - key
                  properties:
                      type:
                          type: string
                          description: The keyboard event type ("keydown", "keyup").
                      key:
                          type: string
                          description: The key pressed or released (e.g., "a", "enter", "shift").
        responses:
            200:
                description: Successfully enqueued keyboard event.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Confirmation of event processing.
            400:
                description: Missing or invalid keyboard event data.
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
