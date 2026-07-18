from __future__ import annotations

from helpers.tool import Response
from tools import response as core_response

from plugins._goal.tools import goal


_CONTINUE_MARKER = "_goal_continue"


class ResponseTool(core_response.ResponseTool):
    async def execute(self, **kwargs) -> Response:
        response = await super().execute(**kwargs)
        current_goal = goal.get_goal(self.agent.context.id)
        if not current_goal or current_goal.get("status") != "active":
            return response

        response.break_loop = False
        response.message = (
            "Goal still active. Continue working autonomously and make safe, in-scope "
            "choices yourself. Call goal update complete when satisfied, or blocked only "
            "when no viable in-scope path remains."
        )
        response.additional = {**(response.additional or {}), _CONTINUE_MARKER: True}
        return response

    async def after_execution(self, response: Response, **kwargs):
        additional = response.additional or {}
        if additional.pop(_CONTINUE_MARKER, False):
            self.agent.hist_add_tool_result(self.name, response.message, **additional)
        await super().after_execution(response, **kwargs)
