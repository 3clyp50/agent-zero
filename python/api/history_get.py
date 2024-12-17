from python.helpers import tokens
from python.helpers.api import ApiHandler
from flask import Request, Response

class GetHistory(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", [])
        context = self.get_context(ctxid)
        agent = context.streaming_agent or context.agent0
        history = agent.history.output()
        size = tokens.approximate_tokens(agent.history.output_text())

        return {
            "history": history,
            "tokens": size
        }

    def get_docstring(self) -> str:
        return """
        Get History API Request
        Retrieve the history of the agent's context.
        ---
        tags:
            -   history
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: GetHistoryRequest
                    required:
                        - context
                    properties:
                        context:
                            type: string
                            description: The context ID to retrieve the history for.
        responses:
            200:
                description: History retrieved successfully.
                schema:
                    type: object
                    properties:
                        history:
                            type: array
                            description: The history of the agent's context.
                        tokens:
                            type: integer
                            description: The approximate number of tokens in the history.
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
