from python.helpers.screen_utils import encode_screenshot, get_screenshot
from python.helpers.tool import Tool, Response


class DescribeScreenTool(Tool):
    async def execute(self, **kwargs):

        screenshot = get_screenshot()

        description = await self.agent.call_vision_model(
            message=self.agent.read_prompt("vision.describe_screen.md"),
            image_url= encode_screenshot(screenshot)
        )

        return Response(message=description, break_loop=False)

    async def after_execution(self, response, **kwargs):
        await self.agent.hist_add_tool_result(self.name, response.message)