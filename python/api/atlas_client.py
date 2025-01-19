import logging
import requests
import base64
from typing import Optional, Tuple
import json
from PIL import Image
import os
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class AtlasClient:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("ATLAS_API_KEY")
        if not self.api_key:
            raise ValueError("ATLAS_API_KEY environment variable is not set")
            
        self.endpoint = endpoint or os.getenv("ATLAS_ENDPOINT", "https://computeragent.pro/api/chat")
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key
        }
        logger.info("AtlasClient initialized.")

    def locate_element(
        self,
        image_path: str,
        prompt: str,
        return_annotated_image: bool = False
    ) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[str]]:
        """
        Call the Atlas API to locate an element on the screen based on a textual description.

        :param image_path: Path to the screenshot image.
        :param prompt: Description of the UI element to locate.
        :param return_annotated_image: Whether to return the annotated image.
        :return: A tuple containing the bounding box coordinates and the annotated image (if requested).
        """
        try:
            # Log image dimensions before sending
            with Image.open(image_path) as img:
                logger.info(f"Image dimensions before sending to Atlas: {img.size}")
            
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            payload = {
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": f"data:image/png;base64,{encoded_image}"}
                    ]
                }]
            }

            logger.info(f"Sending request to Atlas API with prompt: {prompt}")
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30  # Increased timeout to 30 seconds
            )
            response.raise_for_status()
            data = response.json()
            
            # Log the full response for debugging
            logger.debug(f"Atlas API Response: {json.dumps(data, indent=2)}")

            # Extract coordinates from the message content
            try:
                choices = data.get("choices", [])
                if not choices:
                    logger.error("No choices found in Atlas response")
                    return None, None

                message = choices[0].get("message", {})
                content = message.get("content", [])
                if not content:
                    logger.error("No content found in Atlas message")
                    return None, None

                # Find the text content containing coordinates
                coordinate_text = None
                for item in content:
                    if item.get("type") == "text":
                        coordinate_text = item.get("text")
                        break

                if not coordinate_text:
                    logger.error("No text content found in Atlas message")
                    return None, None

                logger.info(f"Raw coordinate text from Atlas: {coordinate_text}")

                # Parse the coordinate string
                coordinates = eval(coordinate_text)[0]  # Format: [[x1, y1, x2, y2]]
                logger.info(f"Successfully parsed coordinates from Atlas: {coordinates}")
                
                # Validate coordinate format
                if len(coordinates) != 4:
                    logger.error(f"Invalid coordinate format. Expected 4 values, got {len(coordinates)}")
                    return None, None
                
                if not all(isinstance(coord, (int, float)) for coord in coordinates):
                    logger.error(f"Invalid coordinate types. All coordinates must be numbers. Got: {coordinates}")
                    return None, None

                # Convert float coordinates to integers and ensure proper tuple type
                coords = tuple(int(coord) for coord in coordinates)
                if len(coords) != 4:
                    logger.error(f"Invalid number of coordinates: {len(coords)}")
                    return None, None
                final_coordinates = (coords[0], coords[1], coords[2], coords[3])
                logger.info(f"Final coordinates (converted to integers): {final_coordinates}")

                annotated_image = data.get("annotated_image")
                if annotated_image:
                    logger.info("Received annotated image from Atlas")
                else:
                    logger.debug("No annotated image in response")

                return final_coordinates, annotated_image

            except (ValueError, IndexError, SyntaxError, AttributeError) as e:
                logger.exception(f"Error parsing Atlas response: {e}")
                return None, None

        except requests.RequestException as e:
            logger.exception(f"Error communicating with Atlas API: {e}")
            return None, None
        except Exception as e:
            logger.exception(f"Unexpected error in locate_element: {e}")
            return None, None

# Initialize the Atlas client using environment variables
atlas_client = AtlasClient() 