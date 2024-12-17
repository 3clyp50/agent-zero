from python.helpers.api import ApiHandler
from flask import Request, Response

class Pause(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # input data
        paused = input.get("paused", False)
        ctxid = input.get("context", "")

        # context instance - get or create
        context = self.get_context(ctxid)

        context.paused = paused

        return {
            "message": "Agent paused." if paused else "Agent unpaused.",
            "pause": paused,
        }

    def get_docstring(self) -> str:
        return """
        Pause API Request
        Pause or unpause the agent.
        ---
        tags:
            -   agent
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: PauseRequest
                    required:
                        - paused
                        - context
                    properties:
                        paused:
                            type: boolean
                            description: Whether the agent should be paused or unpaused.
                        context:
                            type: string
                            description: The context ID for the agent.
        responses:
            200:
                description: Agent paused or unpaused successfully.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Message indicating the status of the agent.
                        pause:
                            type: boolean
                            description: The current pause status of the agent.
            400:
                description: Bad request, missing required parameters.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
