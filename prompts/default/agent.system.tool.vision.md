### vision:
Receive info about the current desktop screen, including visible elements, their position, their styling and more.
Get bounding boxes of specific elements to interact with them.
Never rely on memory for click coordinates

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
        "The user wants me to click on a specific UI element...",
        "I need to use Atlas to get precise coordinates of the element...",
        "I'll enable coordinate detection to get the exact location...",
    ],
    "tool_name": "vision",
    "tool_args": {
        "instruction": "Find the Settings button, which is typically represented by a gear icon.",
        "require_coordinates": true
    }
}
~~~