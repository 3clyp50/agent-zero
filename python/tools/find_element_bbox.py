from python.helpers.askui import get_bbox
from python.helpers.screen_utils import get_screenshot
from python.helpers.tool import Tool, Response


class FindElementBboxTool(Tool):
    async def execute(self, **kwargs):

        screenshot = get_screenshot()

        bbox = await get_bbox(screenshot, self.args.get("description", ""))

        return Response(message=bbox, break_loop=False)