import pyautogui


def move_mouse(x, y, duration=0.25):
    """
    Move the mouse to the specified coordinates.

    :param x: The x-coordinate to move to.
    :param y: The y-coordinate to move to.
    :param duration: The duration of the movement.
    """
    pyautogui.moveTo(x, y, duration=duration)


def click(x=None, y=None, button="left", clicks=1, interval=0.0):
    """
    Perform a mouse click.

    :param x: The x-coordinate to click at.
    :param y: The y-coordinate to click at.
    :param button: The mouse button to click ('left', 'right', 'middle').
    :param clicks: The number of clicks.
    :param interval: The interval between clicks.
    """
    pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)


def type_text(text, interval=0.1):
    """
    Type the specified text.

    :param text: The text to type.
    :param interval: The interval between keystrokes.
    """
    pyautogui.typewrite(text, interval=interval)


def press_key(key):
    """
    Press a single key.

    :param key: The key to press.
    """
    pyautogui.press(key)


def hotkey(*keys):
    """
    Press multiple keys simultaneously (hotkey).

    :param keys: The keys to press.
    """
    pyautogui.hotkey(*keys)


def scroll(clicks, x=None, y=None):
    """
    Scroll the mouse wheel.

    :param clicks: The number of clicks to scroll. Positive for up, negative for down.
    :param x: The x-coordinate to scroll at.
    :param y: The y-coordinate to scroll at.
    """
    pyautogui.scroll(clicks, x=x, y=y)


def drag_to(x, y, duration=0.25, button="left"):
    """
    Drag the mouse to the specified coordinates.

    :param x: The x-coordinate to drag to.
    :param y: The y-coordinate to drag to.
    :param duration: The duration of the drag.
    :param button: The mouse button to hold down during the drag ('left', 'right', 'middle').
    """
    pyautogui.dragTo(x, y, duration=duration, button=button)