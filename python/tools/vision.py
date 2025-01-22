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

import asyncio

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

async def analyze_screen(image_path: Optional[str], element_description: str) -> Optional[Tuple[int, int]]:
    """
    Asynchronously analyze the screen using the Atlas model to find the coordinates of a UI element.
    Returns the center point of the bounding box returned by Atlas.

    :param image_path: Path to the screenshot image. If None, a new screenshot will be captured.
    :param element_description: Description of the UI element to locate.
    :return: A tuple of (x, y) coordinates for the center of the element, or None if not found.
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
            screenshot = await asyncio.to_thread(get_screenshot)
            await asyncio.to_thread(temp_file.write, screenshot)
            await asyncio.to_thread(temp_file.close)  # Close the file handle
            logger.debug(f"Temporary screenshot saved to: {image_path}")

        # Perform the Atlas model call in a separate thread to avoid blocking
        coordinates, annotated_image = await asyncio.to_thread(
            atlas_client.locate_element,
            image_path=image_path,
            prompt=element_description
        )

        if not coordinates:
            logger.error("Failed to locate element using Atlas.")
            return None

        # Calculate the center of the bounding box
        x1, y1, x2, y2 = coordinates
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        logger.info(f"Calculated center coordinates: ({center_x}, {center_y})")

        return center_x, center_y

    finally:
        # Only clean up if we created the temp file and Atlas is done with it
        if temp_path and os.path.exists(temp_path):
            try:
                await asyncio.to_thread(os.unlink, temp_path)
                logger.debug("Temporary screenshot deleted")
            except Exception as e:
                logger.error(f"Error deleting temporary screenshot: {e}")

# Example usage within the vision tool
async def perform_click_action_async(image_path: str, element_description: str):
    """
    Asynchronously perform a mouse click on the specified UI element.

    :param image_path: Path to the screenshot image.
    :param element_description: Description of the UI element to locate and click.
    """
    coordinates = await analyze_screen(image_path, element_description)
    if coordinates:
        x, y = coordinates
        await asyncio.to_thread(pyautogui_handler.click, x=x, y=y)
        logger.info(f"Clicked at coordinates: ({x}, {y})")
    else:
        logger.error("Click action aborted due to failed coordinate retrieval.")

class VisionTool(Tool):
    async def execute(self, **kwargs) -> Response:
        instruction = self.args.get("instruction", "")
        require_coordinates = self.args.get("require_coordinates", False)

        # Get screenshot
        screenshot = await asyncio.to_thread(get_screenshot)
        encoded_screenshot = encode_screenshot(screenshot)

        # Save screenshot if we need coordinates
        temp_file = None
        temp_path = None
        try:
            if require_coordinates:
                # Create a temporary file for the screenshot
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_path = temp_file.name
                await asyncio.to_thread(temp_file.write, screenshot)
                await asyncio.to_thread(temp_file.close)  # Close the file handle
                logger.debug(f"Temporary screenshot saved to: {temp_path}")

            # Create concurrent tasks for vision model and Atlas (if required)
            tasks = []

            # Task for general description from vision model
            vision_task = asyncio.create_task(
                self.agent.call_vision_model(
                    message=instruction,
                    image=encoded_screenshot
                )
            )
            tasks.append(vision_task)

            # Task for Atlas model if coordinates are required
            if require_coordinates and temp_path:
                atlas_task = asyncio.create_task(
                    analyze_screen(temp_path, instruction)
                )
                tasks.append(atlas_task)
            else:
                atlas_task = None

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process vision model result
            description = ""
            if isinstance(results[0], Exception):
                logger.error(f"Vision model failed: {results[0]}")
                description = "Failed to get description from vision model."
            else:
                description = results[0]

            # Process Atlas model result if applicable
            coordinates = None
            if atlas_task:
                atlas_result = results[1]
                if isinstance(atlas_result, Exception):
                    logger.error(f"Atlas model failed: {atlas_result}")
                elif atlas_result:
                    x, y = atlas_result
                    description += f"\nElement located at coordinates: ({x}, {y})"
                    coordinates = (x, y)
                    logger.info(f"Atlas found element at coordinates: ({x}, {y})")
                else:
                    logger.warning("Atlas could not locate the specified element")

            return Response(
                message=description,
                data={"coordinates": coordinates} if coordinates else {},
                break_loop=False
            )

        finally:
            # Only clean up if we created the temp file and Atlas is done with it
            if temp_path and os.path.exists(temp_path):
                try:
                    await asyncio.to_thread(os.unlink, temp_path)
                    logger.debug("Temporary screenshot deleted")
                except Exception as e:
                    logger.error(f"Error deleting temporary screenshot: {e}")

    async def after_execution(self, response, **kwargs) -> None:
        """Add the tool result to history"""
        await self.agent.hist_add_tool_result(self.name, response.message)