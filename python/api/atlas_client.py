import logging
import requests
import base64
from typing import Optional, Tuple, Dict, Union
import json
from PIL import Image
import os
from dotenv import load_dotenv
import re

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
    ) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
        """
        Call the Atlas API to locate an element on the screen based on a textual description.

        Args:
            image_path: Path to the screenshot image.
            prompt: Description of the UI element to locate.
            return_annotated_image: Whether to return the annotated image (unused in framework).

        Returns:
            Tuple containing:
            - Click coordinates as (x, y)
            - Annotated image (always None in framework context)
        """
        try:
            # Get image dimensions for validation and scaling
            with Image.open(image_path) as img:
                img_width, img_height = img.size
                logger.info(f"Image dimensions before sending to Atlas: {img_width}x{img_height}")
            
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
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            try:
                choices = data.get("choices", [])
                if not choices:
                    logger.error("No choices found in Atlas response")
                    return None, None

                message = choices[0].get("message", {})
                content = message.get("content", [])
                
                response_text = next(
                    (item.get("text") for item in content if item.get("type") == "text"),
                    None
                )

                if not response_text:
                    logger.error("No text content found in Atlas message")
                    return None, None

                logger.debug(f"Raw response text: {response_text}")

                # Parse OS-Atlas-Pro-7B format: CLICK <point>[[x,y]]</point>
                click_pattern = r'CLICK <point>\[\[(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\]\]</point>'
                click_match = re.search(click_pattern, response_text)
                
                if click_match:
                    x, y = map(float, click_match.groups())
                    logger.info(f"Found coordinates: ({x}, {y})")
                    
                    # Validate coordinates are within image bounds
                    if not (0 <= x <= img_width and 0 <= y <= img_height):
                        logger.error(f"Coordinates ({x}, {y}) out of bounds for image size {img_width}x{img_height}")
                        return None, None
                    
                    return (int(x), int(y)), None

                logger.warning("No valid coordinates found in response")
                return None, None

            except Exception as e:
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