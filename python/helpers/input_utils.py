from typing import Optional
from desktop_utils import pyautogui_handler


def move_mouse(x: int, y: int, duration: float = 0.25):
    """
    Move the mouse to the specified coordinates.
    """
    pyautogui_handler.move_mouse(x, y, duration)


def click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.0,
):
    """
    Perform a mouse click.
    """
    pyautogui_handler.click(x=x, y=y, button=button, clicks=clicks, interval=interval)


def type_text(text: str, interval: float = 0.1):
    """
    Type the specified text.
    """
    pyautogui_handler.type_text(text, interval)


def press_key(key: str):
    """
    Press a single key.
    """
    pyautogui_handler.press_key(key)


def hotkey(*keys: str):
    """
    Press multiple keys simultaneously (hotkey).
    """
    pyautogui_handler.hotkey(*keys)


def scroll(clicks: int, x: Optional[int] = None, y: Optional[int] = None):
    """
    Scroll the mouse wheel.
    """
    pyautogui_handler.scroll(clicks, x=x, y=y)


def drag_to(x: int, y: int, duration: float = 0.25, button: str = "left"):
    """
    Drag the mouse to the specified coordinates.
    """
    pyautogui_handler.drag_to(x, y, duration, button)
