from python.helpers.api import ApiHandler
from flask import Request, Response

import pyautogui

class ShareKeyboardEvent(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Processes keyboard events and uses PyAutoGUI to replicate them.
        """
        event_type = input.get("type")
        key = input.get("key")

        # Basic validation
        if event_type not in ("keydown", "keyup") or key is None:
            return Response("Invalid keyboard event payload.", status=400)

        if event_type == "keydown":
            pyautogui.keyDown(key)
        elif event_type == "keyup":
            pyautogui.keyUp(key)

        return {
            "message": f"Keyboard event '{event_type}' processed for key '{key}'."
        }

    def get_docstring(self) -> str:
        return """
        Keyboard Events API
        Receives keyboard events (keydown, keyup) and replicates them with PyAutoGUI.
        ---
        tags:
            -   screen
        parameters:
            -   in: body
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
                            description: The key pressed or released (e.g. "a", "enter", "shift").
        responses:
            200:
                description: Successfully processed keyboard event.
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
        """

    def get_supported_http_method(self) -> str:
        return "POST"
