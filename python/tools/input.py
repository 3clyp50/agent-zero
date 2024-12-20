from python.helpers.tool import Tool, Response
from python.helpers.input_utils import move_mouse, click, type_text, press_key, hotkey, scroll, drag_to

class Input(Tool):

    async def execute(self, action=None, **kwargs):
        if action == "move_mouse":
            return self.move_mouse(**kwargs)
        elif action == "click":
            return self.click(**kwargs)
        elif action == "type_text":
            return self.type_text(**kwargs)
        elif action == "press_key":
            return self.press_key(**kwargs)
        elif action == "hotkey":
            return self.hotkey(**kwargs)
        elif action == "scroll":
            return self.scroll(**kwargs)
        elif action == "drag_to":
            return self.drag_to(**kwargs)
        else:
            return Response(message="Invalid action specified.", break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(type="input", heading=f"{self.agent.agent_name}: Using tool '{self.name}'", content="", kvps=self.args)

    async def after_execution(self, response, **kwargs):
        await self.agent.hist_add_tool_result(self.name, response.message)

    def move_mouse(self, x, y, duration=0.25):
        move_mouse(x, y, duration)
        return Response(message=f"Moved mouse to ({x}, {y}) with duration {duration}.", break_loop=False)

    def click(self, x=None, y=None, button="left", clicks=1, interval=0.0):
        click(x, y, button, clicks, interval)
        return Response(message=f"Clicked at ({x}, {y}) with button '{button}' {clicks} times with interval {interval}.", break_loop=False)

    def type_text(self, text, interval=0.1):
        type_text(text, interval)
        return Response(message=f"Typed text: '{text}' with interval {interval}.", break_loop=False)

    def press_key(self, key):
        press_key(key)
        return Response(message=f"Pressed key: '{key}'.", break_loop=False)

    def hotkey(self, keys):
        hotkey(*keys)
        return Response(message=f"Pressed hotkey: {', '.join(keys)}.", break_loop=False)

    def scroll(self, clicks, x=None, y=None):
        scroll(clicks, x, y)
        return Response(message=f"Scrolled {clicks} clicks at ({x}, {y}).", break_loop=False)

    def drag_to(self, x, y, duration=0.25, button="left"):
        drag_to(x, y, duration, button)
        return Response(message=f"Dragged to ({x}, {y}) with duration {duration} using button '{button}'.", break_loop=False)
