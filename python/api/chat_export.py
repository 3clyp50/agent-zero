from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers import persist_chat


class ExportChat(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("ctxid", "")
        if not ctxid:
            raise Exception("No context id provided")

        context = self.get_context(ctxid)
        content = persist_chat.export_json_chat(context)
        return {
            "message": "Chats exported.",
            "ctxid": context.id,
            "content": content,
        }

    def get_docstring(self) -> str:
        return """
        Export Chat API Request
        Export the chat history.
        ---
        tags:
            -   chat
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: ExportChatRequest
                    required:
                        - ctxid
                    properties:
                        ctxid:
                            type: string
                            description: The context ID of the chat to be exported.
        responses:
            200:
                description: Successful chat export.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: A message indicating the status of the export.
                        ctxid:
                            type: string
                            description: The context ID of the exported chat.
                        content:
                            type: string
                            description: The exported chat content in JSON format.
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
