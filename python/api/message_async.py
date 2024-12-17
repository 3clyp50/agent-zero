from agent import AgentContext
from python.helpers.defer import DeferredTask
from python.api.message import Message

class MessageAsync(Message):
    async def respond(self, task: DeferredTask, context: AgentContext):
        return {
            "message": "Message received.",
            "context": context.id,
        }

    def get_docstring(self) -> str:
        return """
        Message Async API
        Handle asynchronous messages.
        ---
        tags:
            - message
        parameters:
            - in: body
              name: body
              required: true
              schema:
                  id: MessageAsyncRequest
                  properties:
                      task:
                          type: object
                          description: The deferred task object.
                      context:
                          type: object
                          description: The agent context object.
        responses:
            200:
                description: Message received successfully.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Confirmation message.
                        context:
                            type: string
                            description: The context ID.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
