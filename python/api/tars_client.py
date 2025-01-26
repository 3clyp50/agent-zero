import logging
import requests
import base64
from typing import Optional, Tuple, Union, Dict
import json
from PIL import Image
import os
import re
from dotenv import load_dotenv

# Initialize logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class UI_TARS_Client:
    def __init__(self, api_key: Optional[str] = None, endpoint: Optional[str] = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("UI_TARS_API_KEY", "empty")  # Default to 'empty' as per guidance
        self.endpoint = endpoint or os.getenv("UI_TARS_ENDPOINT", "http://127.0.0.1:8000/v1/chat/completions")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.debug("UI_TARS_Client initialized.")

    def locate_element(
        self,
        image_path: str,
        instruction: str,
        return_annotated_image: bool = False
    ) -> Tuple[Optional[Dict[str, Union[Tuple[int, int], Tuple[int, int, int, int]]]], Optional[str]]:
        """
        Call the UI-TARS API to perform a GUI action based on a textual description and screenshot.

        :param image_path: Path to the screenshot image.
        :param instruction: Description of the task to perform.
        :param return_annotated_image: Whether to return the annotated image.
        :return: A tuple containing action details and the annotated image (if requested).
        """
        try:
            # Log image dimensions before sending
            with Image.open(image_path) as img:
                image_width, image_height = img.size
                logger.info(f"Image dimensions: width={image_width}, height={image_height}")

            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Prepare the prompt as per UI-TARS guidance
            prompt = self.create_prompt(instruction)

            payload = {
                "model": "ui-tars",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}
                        ],
                    },
                ],
                "frequency_penalty": 1,
                "max_tokens": 128
            }

            logger.info(f"Sending request to UI-TARS API with instruction: {instruction}")
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=60  # Increased timeout to accommodate processing time
            )
            response.raise_for_status()
            data = response.json()

            # Log the full response for debugging
            logger.debug(f"UI-TARS API Response: {json.dumps(data, indent=2)}")

            # Extract the content from the response
            try:
                choices = data.get("choices", [])
                if not choices:
                    logger.error("No choices found in UI-TARS response")
                    return None, None

                message = choices[0].get("message", {})
                content = message.get("content", "")
                if not content:
                    logger.error("No content found in UI-TARS message")
                    return None, None

                logger.info(f"Raw content from UI-TARS: {content}")

                # Parse the content to extract Thought and Action
                thought, action = self.parse_content(content)
                if not action:
                    logger.error("No Action found in UI-TARS content")
                    return None, None

                logger.info(f"Extracted Thought: {thought}")
                logger.info(f"Extracted Action: {action}")

                # Parse the Action to extract relevant coordinates
                action_details = self.parse_action(action, image_width, image_height)
                if not action_details:
                    logger.error("Failed to parse Action details")
                    return None, None

                annotated_image = data.get("annotated_image") if return_annotated_image else None
                if annotated_image:
                    logger.info("Received annotated image from UI-TARS")
                else:
                    logger.debug("No annotated image in response")

                return action_details, annotated_image

            except (ValueError, IndexError, SyntaxError, AttributeError) as e:
                logger.exception(f"Error parsing UI-TARS response: {e}")
                return None, None

        except requests.RequestException as e:
            logger.exception(f"Error communicating with UI-TARS API: {e}")
            return None, None
        except Exception as e:
            logger.exception(f"Unexpected error in locate_element: {e}")
            return None, None

    def create_prompt(self, instruction: str) -> str:
        """
        Creates the prompt for the UI-TARS model.

        :param instruction: The instruction or task for the model.
        :return: The formatted prompt.
        """
        prompt = f"""You are a GUI agent. You are given a task and your action history, with screenshots. You need to perform the next action to complete the task. 

## Output Format
```
Thought: ...
Action: ...
```

## Action Space

click(start_box='<|box_start|>(x1,y1)<|box_end|>')
left_double(start_box='<|box_start|>(x1,y1)<|box_end|>')
right_single(start_box='<|box_start|>(x1,y1)<|box_end|>')
drag(start_box='<|box_start|>(x1,y1)<|box_end|>', end_box='<|box_start|>(x3,y3)<|box_end|>')
hotkey(key='')
type(content='') #If you want to submit your input, use "\\"
 at the end of `content`.
scroll(start_box='<|box_start|>(x1,y1)<|box_end|>', direction='down or up or right or left')
wait() #Sleep for 5s and take a screenshot to check for any changes.
finished()
call_user() # Submit the task and call the user when the task is unsolvable, or when you need the user's help.

## Note
- Use Chinese in `Thought` part.
- Summarize your next action (with its target element) in one sentence in `Thought` part.

## User Instruction
{instruction}
"""
        return prompt

    def parse_content(self, content: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parses the model's response content to extract Thought and Action.

        :param content: The raw content string from the model's response.
        :return: A tuple containing Thought and Action strings.
        """
        thought = None
        action = None

        # Regular expressions to extract Thought and Action
        thought_pattern = re.compile(r"Thought:\s*(.*)", re.IGNORECASE)
        action_pattern = re.compile(r"Action:\s*(.*)", re.IGNORECASE)

        thought_match = thought_pattern.search(content)
        action_match = action_pattern.search(content)

        if thought_match:
            thought = thought_match.group(1).strip()
        if action_match:
            action = action_match.group(1).strip()

        return thought, action

    def parse_action(self, action: str, image_width: int, image_height: int) -> Optional[Dict[str, Union[Tuple[int, int], Tuple[int, int, int, int]]]]:
        """
        Parses the Action string to extract command and coordinates.

        :param action: The Action string from the model's response.
        :param image_width: Width of the image in pixels.
        :param image_height: Height of the image in pixels.
        :return: A dictionary with action details and absolute coordinates.
        """
        # Define regex patterns for different actions
        action_patterns = {
            'click': re.compile(r"click\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'\)"),
            'left_double': re.compile(r"left_double\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'\)"),
            'right_single': re.compile(r"right_single\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'\)"),
            'drag': re.compile(r"drag\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>',\s*end_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>'\)"),
            'hotkey': re.compile(r"hotkey\(key='(.*)'\)"),
            'type': re.compile(r"type\(content='(.*)'\)"),
            'scroll': re.compile(r"scroll\(start_box='<\|box_start\|>\((\d+),(\d+)\)<\|box_end\|>',\s*direction='(up|down|left|right)'\)"),
            # Add more patterns as needed
        }

        for action_type, pattern in action_patterns.items():
            match = pattern.match(action)
            if match:
                if action_type in ['click', 'left_double', 'right_single']:
                    rel_x, rel_y = float(match.group(1)), float(match.group(2))
                    abs_x, abs_y = self.map_coordinates(rel_x, rel_y, image_width, image_height)
                    logger.debug(f"Action '{action_type}' with absolute coordinates: ({abs_x}, {abs_y})")
                    return {
                        "action": action_type,
                        "coordinates": (abs_x, abs_y)
                    }

                elif action_type == 'drag':
                    rel_x1, rel_y1, rel_x2, rel_y2 = map(float, match.groups())
                    abs_x1, abs_y1 = self.map_coordinates(rel_x1, rel_y1, image_width, image_height)
                    abs_x2, abs_y2 = self.map_coordinates(rel_x2, rel_y2, image_width, image_height)
                    logger.debug(f"Action 'drag' from ({abs_x1}, {abs_y1}) to ({abs_x2}, {abs_y2})")
                    return {
                        "action": "drag",
                        "start_coordinates": (abs_x1, abs_y1),
                        "end_coordinates": (abs_x2, abs_y2)
                    }

                elif action_type == 'hotkey':
                    key = match.group(1)
                    logger.debug(f"Action 'hotkey' with key: {key}")
                    return {
                        "action": "hotkey",
                        "key": key
                    }

                elif action_type == 'type':
                    content = match.group(1)
                    logger.debug(f"Action 'type' with content: {content}")
                    return {
                        "action": "type",
                        "content": content
                    }

                elif action_type == 'scroll':
                    rel_x, rel_y, direction = match.groups()
                    abs_x, abs_y = self.map_coordinates(float(rel_x), float(rel_y), image_width, image_height)
                    logger.debug(f"Action 'scroll' at ({abs_x}, {abs_y}) with direction: {direction}")
                    return {
                        "action": "scroll",
                        "coordinates": (abs_x, abs_y),
                        "direction": direction
                    }

                # Extend with additional action types as needed

        logger.error(f"Unrecognized action format: {action}")
        return None

    def map_coordinates(self, relative_x: float, relative_y: float, image_width: int, image_height: int) -> Tuple[int, int]:
        """
        Maps relative coordinates to absolute pixel values.

        :param relative_x: Relative X coordinate (0-1000).
        :param relative_y: Relative Y coordinate (0-1000).
        :param image_width: Width of the image in pixels.
        :param image_height: Height of the image in pixels.
        :return: A tuple of absolute (X, Y) coordinates.
        """
        absolute_x = round(image_width * relative_x / 1000)
        absolute_y = round(image_height * relative_y / 1000)
        logger.debug(f"Mapped relative ({relative_x}, {relative_y}) to absolute ({absolute_x}, {absolute_y})")
        return absolute_x, absolute_y

# Example usage
if __name__ == "__main__":
    # Initialize the UI-TARS client using environment variables or default values
    ui_tars_client = UI_TARS_Client()

    # Define the instruction and image path
    instruction = "search for today's weather"
    screenshot_path = "screenshot.png"  # Ensure this image exists in the same directory

    # Call locate_element
    action_details, annotated_image = ui_tars_client.locate_element(
        image_path=screenshot_path,
        instruction=instruction,
        return_annotated_image=False  # Set to True if you want the annotated image
    )

    if action_details:
        logger.info(f"Action Details: {action_details}")
    else:
        logger.warning("No action details received.")

    if annotated_image:
        # Save the annotated image if needed
        with open("annotated_screenshot.png", "wb") as f:
            f.write(base64.b64decode(annotated_image))
        logger.info("Annotated image saved as 'annotated_screenshot.png'")