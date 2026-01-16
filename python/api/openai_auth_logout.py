from python.helpers.api import ApiHandler, Request, Response
from python.helpers import openai_auth


class OpenaiAuthLogout(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        openai_auth.clear_auth()
        return {"ok": True}
