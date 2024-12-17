from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import persist_chat

class LoadChats(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        chats = input.get("chats", [])
        if not chats:
            raise Exception("No chats provided")

        ctxids = persist_chat.load_json_chats(chats)

        return {
            "message": "Chats loaded.",
            "ctxids": ctxids,
        }

    def get_docstring(self) -> str:
        return """
        Load Chats API Request
        Load new chats.
        ---
        tags:
            -   chat
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: LoadChatsRequest
                    required:
                        - chats
                    properties:
                        chats:
                            type: array
                            items:
                                type: object
                            description: List of chat objects to be loaded.
        responses:
            200:
                description: Successful chat loading.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: A message indicating the status of the chat loading.
                        ctxids:
                            type: array
                            items:
                                type: string
                            description: List of context IDs of the loaded chats.
            400:
                description: Bad request, missing chats.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
