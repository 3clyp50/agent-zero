from python.helpers import tokens
from python.helpers.api import ApiHandler
from flask import Request, Response

class GetCtxWindow(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", [])
        context = self.get_context(ctxid)
        agent = context.streaming_agent or context.agent0
        window = agent.get_data(agent.DATA_NAME_CTX_WINDOW)
        size = tokens.approximate_tokens(window)

        return {"content": window, "tokens": size}

    def get_docstring(self) -> str:
        return """
        Get Context Window API Request
        Retrieve the context window for the given context ID.
        ---
        tags:
            - context
        parameters:
            - in: body
              name: body
              required: true
              schema:
                  id: GetCtxWindowRequest
                  required:
                      - context
                  properties:
                      context:
                          type: string
                          description: The context ID to retrieve the context window for.
        responses:
            200:
                description: Context window retrieved successfully.
                schema:
                    type: object
                    properties:
                        content:
                            type: string
                            description: The content of the context window.
                        tokens:
                            type: integer
                            description: The approximate number of tokens in the context window.
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
