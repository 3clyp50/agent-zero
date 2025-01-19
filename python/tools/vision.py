from python.helpers.screen_utils import encode_screenshot, get_screenshot
from python.helpers.tool import Tool, Response
import logging
import base64
import os
import tempfile
from datetime import datetime
from typing import Optional, Tuple

from python.api.atlas_client import atlas_client
from python.helpers.desktop_utils import pyautogui_handler

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def analyze_screen(image_path: Optional[str], element_description: str) -> Optional[Tuple[int, int]]:
    """
    Analyze the screen using the Atlas model to find the coordinates of a UI element.
    Returns the coordinates returned by Atlas.

    :param image_path: Path to the screenshot image. If None, a new screenshot will be captured.
    :param element_description: Description of the UI element to locate.
    :return: A tuple of (x, y) coordinates for clicking the element, or None if not found.
    """
    temp_file = None
    temp_path = None
    try:
        # If no image path provided, capture and save a new screenshot
        if image_path is None:
            # Create a temporary file for the screenshot
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            image_path = temp_path
            screenshot = get_screenshot()
            temp_file.write(screenshot)
            temp_file.close()  # Close the file handle immediately
            logger.debug(f"Temporary screenshot saved to: {image_path}")

        coordinates, _ = atlas_client.locate_element(
            image_path=image_path,
            prompt=element_description
        )

        if not coordinates:
            logger.error("Failed to locate element using Atlas.")
            return None

        logger.info(f"Atlas returned coordinates: {coordinates}")
        return coordinates

    finally:
        # Only clean up if we created the temp file and Atlas is done with it
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
                logger.debug("Temporary screenshot deleted")
            except Exception as e:
                logger.error(f"Error deleting temporary screenshot: {e}")

# Example usage within the vision tool
def perform_click_action(image_path: str, element_description: str):
    """
    Perform a mouse click on the specified UI element.

    :param image_path: Path to the screenshot image.
    :param element_description: Description of the UI element to locate and click.
    """
    coordinates = analyze_screen(image_path, element_description)
    if coordinates:
        x, y = coordinates
        pyautogui_handler.click(x=x, y=y)
        logger.info(f"Clicked at coordinates: ({x}, {y})")
    else:
        logger.error("Click action aborted due to failed coordinate retrieval.")

class VisionTool(Tool):
    async def execute(self, **kwargs) -> Response:
        instruction = self.args.get("instruction", "")
        require_coordinates = self.args.get("require_coordinates", False)

        # Get screenshot
        screenshot = get_screenshot()
        encoded_screenshot = encode_screenshot(screenshot)

        # Save screenshot if we need coordinates
        temp_file = None
        temp_path = None
        try:
            if require_coordinates:
                # Create a temporary file for the screenshot
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                temp_file.write(screenshot)
                temp_file.close()  # Close the file handle immediately
                logger.debug(f"Temporary screenshot saved to: {temp_path}")

            # Get general description from vision model
            description = await self.agent.call_vision_model(
                message=instruction,
                image=encoded_screenshot
            )

            # If coordinates are required, use Atlas to get precise location
            coordinates = None
            if require_coordinates and temp_path:
                try:
                    coordinates = analyze_screen(temp_path, instruction)
                    if coordinates:
                        x, y = coordinates
                        description += f"\nElement located at coordinates: ({x}, {y})"
                        logger.info(f"Atlas found element at coordinates: ({x}, {y})")
                    else:
                        logger.warning("Atlas could not locate the specified element")
                except Exception as e:
                    logger.error(f"Error using Atlas for coordinate detection: {e}")

            return Response(
                message=description,
                data={"coordinates": coordinates} if coordinates else {},
                break_loop=False
            )

        finally:
            # Only clean up if we created the temp file and Atlas is done with it
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.debug("Temporary screenshot deleted")
                except Exception as e:
                    logger.error(f"Error deleting temporary screenshot: {e}")

    async def after_execution(self, response, **kwargs) -> None:
        """Add the tool result to history"""
        await self.agent.hist_add_tool_result(self.name, response.message)