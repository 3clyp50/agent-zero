from python.helpers.api import ApiHandler
from flask import Request, Response

from agent import AgentContext


class Poll(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", None)
        from_no = input.get("log_from", 0)

        # context instance - get or create
        context = self.get_context(ctxid)

        logs = context.log.output(start=from_no)

        # loop AgentContext._contexts
        ctxs = []
        for ctx in AgentContext._contexts.values():
            ctxs.append(
                {
                    "id": ctx.id,
                    "no": ctx.no,
                    "log_guid": ctx.log.guid,
                    "log_version": len(ctx.log.updates),
                    "log_length": len(ctx.log.logs),
                    "paused": ctx.paused,
                }
            )

        response_data = {
            "context": context.id,
            "contexts": ctxs,
            "logs": logs,
            "log_guid": context.log.guid,
            "log_version": len(context.log.updates),
            "log_progress": context.log.progress,
            "log_progress_active": context.log.progress_active,
            "paused": context.paused,
        }

        return response_data

    def get_docstring(self) -> str:
        return """
        Poll API Request
        Poll the logs and context information.
        ---
        tags:
          - logs
        parameters:
          - in: body
            name: body
            required: true
            schema:
              type: object
              required:
                - context
              properties:
                context:
                  type: string
                  description: The context ID.
                log_from:
                  type: integer
                  description: The starting log number.
        responses:
          200:
            description: Polling successful.
            schema:
              type: object
              properties:
                context:
                  type: string
                  description: The context ID.
                contexts:
                  type: array
                  items:
                    type: object
                logs:
                  type: array
                  items:
                    type: string
                    description: The log entries.
                log_guid:
                  type: string
                  description: The log GUID.
                log_version:
                  type: integer
                  description: The log version.
                log_progress:
                  type: integer
                  description: The log progress.
                log_progress_active:
                  type: boolean
                  description: Whether the log progress is active.
                paused:
                  type: boolean
                  description: Whether the context is paused.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
