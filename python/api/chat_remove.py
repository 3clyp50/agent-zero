from python.helpers.api import ApiHandler
from flask import Request, Response

from agent import AgentContext
from python.helpers import persist_chat

class RemoveChat(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", "")

        # context instance - get or create
        AgentContext.remove(ctxid)
        persist_chat.remove_chat(ctxid)

        return {
            "message": "Context removed.",
        }

    def get_docstring(self) -> str:
        return """
        Remove Chat API Request
        Remove a chat context.
        ---
        tags:
            -   chat
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: RemoveChatRequest
                    required:
                        - context
                    properties:
                        context:
                            type: string
                            description: The context ID of the chat to be removed.
        responses:
            200:
                description: Successful removal of the chat context.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: A message indicating the context has been removed.
            400:
                description: Bad request, missing context ID.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
