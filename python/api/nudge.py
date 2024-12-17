from python.helpers.api import ApiHandler
from flask import Request, Response

class Nudge(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("ctxid", "")
        if not ctxid:
            raise Exception("No context id provided")

        context = self.get_context(ctxid)
        context.nudge()

        msg = "Process reset, agent nudged."
        context.log.log(type="info", content=msg)

        return {
            "message": msg,
            "ctxid": context.id,
        }

    def get_docstring(self) -> str:
        return """
        Nudge API Request
        Nudge the agent to reset the process.
        ---
        tags:
            -   agent
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: NudgeRequest
                    required:
                        - ctxid
                    properties:
                        ctxid:
                            type: string
                            description: The context ID to nudge.
        responses:
            200:
                description: Agent nudged successfully.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Success message.
                        ctxid:
                            type: string
                            description: The context ID that was nudged.
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
