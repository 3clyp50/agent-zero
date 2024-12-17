from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import settings

class GetSettings(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        set = settings.convert_out(settings.get_settings())
        return {"settings": set}

    def get_docstring(self) -> str:
        return """
        Get Settings API
        Retrieve the settings of the service.
        ---
        tags:
            - settings
        responses:
            200:
                description: Settings retrieved successfully.
                schema:
                    type: object
                    properties:
                        settings:
                            type: object
                            description: The settings of the service.
        """

    def get_supported_http_method(self) -> str:
        return "GET"
