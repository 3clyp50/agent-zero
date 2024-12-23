from python.helpers.api import ApiHandler
from flask import Request, Response

import pyautogui

class ShareMouseEvent(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Processes mouse events and uses PyAutoGUI to replicate them.
        """
        event_type = input.get("type")
        x = input.get("x")
        y = input.get("y")
        button = input.get("button", "left")

        # Basic validation
        if event_type not in ("move", "down", "up") or x is None or y is None:
            return Response("Invalid mouse event payload.", status=400)
        
        if event_type == "move":
            # Move mouse smoothly to (x, y)
            pyautogui.moveTo(x, y, duration=0.0)
        elif event_type == "down":
            # Press mouse button down
            pyautogui.mouseDown(x=x, y=y, button=button)
        elif event_type == "up":
            # Release mouse button
            pyautogui.mouseUp(x=x, y=y, button=button)

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
        """

    def get_supported_http_method(self) -> str:
        return "POST"
