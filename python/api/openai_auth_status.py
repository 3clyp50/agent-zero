from python.helpers.api import ApiHandler, Request, Response
from python.helpers import openai_auth


class OpenaiAuthStatus(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        return openai_auth.get_auth_status()
