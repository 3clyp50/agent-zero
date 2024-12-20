import base64
import pyautogui
from io import BytesIO
from PIL import ImageDraw

def get_screenshot() -> bytes:
    # Capture the screenshot
    screenshot = pyautogui.screenshot()

    # Get the mouse position
    mouse_x, mouse_y = pyautogui.position()

    # Draw the mouse cursor on the screenshot
    draw = ImageDraw.Draw(screenshot)

    # Define the mouse pointer shape as a polygon
    pointer_points = [
        (14.781, 5.0),
        (14.0, 6.156),
        (14.0, 39.0),
        (14.609, 39.914),
        (15.688, 39.719),
        (22.938, 32.906),
        (28.781, 46.406),
        (35.0, 43.594),
        (28.906, 30.281),
        (39.977, 28.73),
        (39.688, 27.656),
        (15.844, 5.438),
        (14.781, 5.0)
    ]

    # Scale the points to a visible size
    scale_factor = 0.75 # Adjust this value to change the size of the pointer
    scaled_points = [(x * scale_factor, y * scale_factor) for x, y in pointer_points]

    # Translate the points to the mouse position
    translated_points = [(mouse_x + x, mouse_y + y) for x, y in scaled_points]

    # Draw the polygon
    draw.polygon(translated_points, fill="white", outline="black", width=2)

    # Convert the screenshot to RGB mode
    screenshot = screenshot.convert("RGB")

    # Save the screenshot to a bytes buffer
    buffer = BytesIO()
    screenshot.save(buffer, format="JPEG", quality=75)

    return buffer.getvalue()

def encode_screenshot(screenshot) -> str:
    return base64.b64encode(screenshot).decode("utf-8")