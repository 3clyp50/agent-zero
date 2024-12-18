### input:
use keyboard arg for terminal program input
answer dialogues enter passwords etc
not for browser
usage:
Use the input tool to perform various input actions such as moving the mouse, clicking, typing text, pressing keys, using hotkeys, scrolling, and dragging.

#### Supported Actions:
- **move_mouse:** Move the mouse to specified coordinates.
- **click:** Perform a mouse click.
- **type_text:** Type specified text.
- **press_key:** Press a single key.
- **hotkey:** Press multiple keys simultaneously (hotkey).
- **scroll:** Scroll the mouse wheel.
- **drag_to:** Drag the mouse to specified coordinates

**Example usage**:

1. Move mouse
~~~json
{
    "thoughts": [
        "Need to move the mouse to coordinates (100, 200)."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "move_mouse",
        "x": 100,
        "y": 200,
        "duration": 0.25
    }
}
~~~

2. Click
~~~json
{
    "thoughts": [
        "Need to click at coordinates (150, 250)."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "click",
        "x": 150,
        "y": 250,
        "button": "left",
        "clicks": 1,
        "interval": 0.0
    }
}
~~~

3. Type Text
~~~json
{
    "thoughts": [
        "Need to type the text 'Hello, World!'."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "type_text",
        "text": "Hello, World!",
        "interval": 0.1
    }
}
~~~

4. Press key
~~~json
{
    "thoughts": [
        "Need to press the 'enter' key."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "press_key",
        "key": "enter"
    }
}
~~~

5. Use hotkey
~~~json
{
    "thoughts": [
        "Need to press the hotkey 'ctrl' + 'c'."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "hotkey",
        "keys": ["ctrl", "c"]
    }
}
~~~

6. Scroll
~~~json
{
    "thoughts": [
        "Need to scroll up by 5 clicks."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "scroll",
        "clicks": 5
    }
}
~~~

7. Drag mouse
~~~json
{
    "thoughts": [
        "Need to drag the mouse to coordinates (300, 400)."
    ],
    "tool_name": "input",
    "tool_args": {
        "action": "drag_to",
        "x": 300,
        "y": 400,
        "duration": 0.25,
        "button": "left"
    }
}
~~~