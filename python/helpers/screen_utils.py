import base64
from PIL import ImageGrab
from io import BytesIO

def get_screenshot() -> bytes:
    screenshot = ImageGrab.grab()
    buffer = BytesIO()
    screenshot.convert("RGB").save(buffer, format="JPEG", quality=75)
    return buffer.getvalue()

def encode_screenshot(screenshot) -> str:
    return base64.b64encode(screenshot).decode("utf-8")