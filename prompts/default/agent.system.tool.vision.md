### vision:
Receive info about the current desktop screen, including visible elements, their position, their styling and more.
Get bounding boxes of specific elements to interact with them.

**Example usages**:
~~~json
{
    "thoughts": [
        "The user wants me to interact with a GUI application...",
        "First I need to get a comprehensive description of the screen to understand what I'm currently looking at to then pick the best action...",
    ],
    "tool_name": "vision",
    "tool_args": {
        "instruction": """Provide a comprehensive and vivid description of the provided screenshot.
Here are the key aspects you should focus on:

**Detailed Elements:**

Break down the image into its constituent elements and describe each one in detail.
Include information about colors, textures, shapes, sizes and types (button, textarea, dropdown, icon, etc).

**Spatial Relationships:**

Describe the overall layout and the position of each element in relation to the screen.
Explain the spatial relationships between different elements in the image.

**Unique or Noteworthy Features:**

Highlight any unique, unusual, or noteworthy features of the image.
Mention any symbols, icons, text, or other significant details.
        """
    }
}
~~~

~~~json
{
    "thoughts": [
        "The user wants me to close the current window...",
        "I already know that I'm currently looking at a window of a text editor window, with a black X in the top right corner...",
        "The X in the top right corner generally indicates a close button...",
        "I need to get the bounding box of this element to further interact with it...",
    ],
    "tool_name": "vision",
    "tool_args": {
        "instruction": "Return a bounding box of the blakc X in the top right corner, which indicates a close button. Use a tuple like [x_start, y_start, x_end, y_end] to represent the bounding box."
    }
}
~~~