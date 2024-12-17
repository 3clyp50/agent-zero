from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import git

class HealthCheck(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        gitinfo = git.get_git_info()
        return {"gitinfo": gitinfo}

    def get_docstring(self) -> str:
        return """
        Health Check API
        Check the health of the service.
        ---
        tags:
            - health
        responses:
            200:
                description: Health check successful.
                schema:
                    type: object
                    properties:
                        gitinfo:
                            type: object
                            description: Information about the Git repository.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
