from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import persist_chat

class Reset(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", "")

        # context instance - get or create
        context = self.get_context(ctxid)
        context.reset()
        persist_chat.save_tmp_chat(context)

        return {
            "message": "Agent restarted.",
        }

    def get_docstring(self) -> str:
        return """
        Reset API Request
        Reset the agent's context.
        ---
        tags:
            -   chat
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: ResetRequest
                    required:
                        - context
                    properties:
                        context:
                            type: string
                            description: The context ID to reset.
        responses:
            200:
                description: Agent restarted successfully.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Confirmation message indicating the agent has been restarted.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
