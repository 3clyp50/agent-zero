from __future__ import annotations

from agent import LoopData
from helpers.extension import Extension
from plugins._goal.tools import goal


class IncludeGoal(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        if not self.agent:
            return

        try:
            current_goal = goal.get_goal(self.agent.context.id)
        except ValueError:
            current_goal = None

        if not current_goal or current_goal.get("status") != "active":
            loop_data.extras_temporary.pop("current_goal", None)
            return

        loop_data.extras_temporary["current_goal"] = self.agent.read_prompt(
            "agent.extras.goal.md",
            status=current_goal.get("status", ""),
            objective=current_goal.get("objective", ""),
            created_by=current_goal.get("created_by", ""),
            updated_at=current_goal.get("updated_at", ""),
        )
