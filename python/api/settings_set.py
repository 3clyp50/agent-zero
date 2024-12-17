from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import settings

class SetSettings(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        set = settings.convert_in(input)
        set = settings.set_settings(set)
        return {"settings": set}

    def get_docstring(self) -> str:
        return """
        Set Settings API
        Set the settings for the service.
        ---
        tags:
            - settings
        parameters:
            - in: body
              name: body
              required: true
              schema:
                  id: SetSettingsRequest
                  required:
                      - setting1
                      - setting2
                  properties:
                      setting1:
                          type: string
                          description: Description of setting1
                      setting2:
                          type: integer
                          description: Description of setting2
        responses:
            200:
                description: Settings updated successfully.
                schema:
                    type: object
                    properties:
                        settings:
                            type: object
                            description: The updated settings.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
