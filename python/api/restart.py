from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import process

class Restart(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        process.reload()
        return Response(status=200)

    def get_docstring(self) -> str:
        return """
        Restart API Request
        Restart the service.
        ---
        tags:
            -   service
        responses:
            200:
                description: Service restarted successfully.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
