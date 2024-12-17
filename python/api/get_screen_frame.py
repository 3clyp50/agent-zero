from python.helpers.api import ApiHandler
from flask import Request, Response, jsonify

from python.helpers.screen_sharer import ScreenSharer

screen_sharer = ScreenSharer()

class ShareScreen(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        frame = screen_sharer.get_frame()
        if not frame:
            raise Exception("No frames available yet.")

        return {"frame": frame}

    def get_docstring(self) -> str:
        return """
        Share Screen API
        ---
        tags:
            -   screen
        responses:
            200:
                description: Screen frame retrieved successfully.
                schema:
                    type: object
                    properties:
                        frame:
                            type: string
                            description: The current screen frame.
            500:
                description: Internal server error, no frames available.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "GET"
