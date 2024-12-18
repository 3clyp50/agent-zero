import warnings
import torch
from transformers import AutoModelForCausalLM, AutoProcessor
import asyncio
from python.helpers import runtime
from python.helpers.print_style import PrintStyle
from PIL import Image
import io

# Suppress FutureWarning from torch.load
warnings.filterwarnings("ignore", category=FutureWarning)

_model = None
_processor = None
_model_name = ""
is_updating_model = False

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

async def preload():
    try:
        return await runtime.call_development_function(_preload)
    except Exception as e:
        if not runtime.is_development():
            raise e

async def _preload():
    global _model, _processor, _model_name, is_updating_model

    while is_updating_model:
        await asyncio.sleep(0.1)

    try:
        is_updating_model = True
        if not _model:
            PrintStyle.standard(f"Loading model: AskUI/PTA-1")
            _model = AutoModelForCausalLM.from_pretrained("AskUI/PTA-1", trust_remote_code=True).to(device, torch_dtype)
            _processor = AutoProcessor.from_pretrained("AskUI/PTA-1", trust_remote_code=True)
    finally:
        is_updating_model = False

async def is_downloading():
    return await runtime.call_development_function(_is_downloading)

def _is_downloading():
    return is_updating_model

async def get_bbox(image_bytes: bytes, text_input: str):
    return await runtime.call_development_function(_get_bbox, image_bytes, text_input)

async def _get_bbox(image_bytes: bytes, text_input: str):
    await _preload()

    if not _processor:
        raise Exception("askui processor is not available.")

    if not _model:
        raise Exception("askui model is not available.")

    # Process the image and text input
    task_prompt = "<OPEN_VOCABULARY_DETECTION>"
    prompt = task_prompt + text_input

    # Open the image from bytes
    image = Image.open(io.BytesIO(image_bytes))

    # Process the image and text input
    task_prompt = "<OPEN_VOCABULARY_DETECTION>"
    prompt = task_prompt + text_input

    image = image.convert("RGB")

    inputs = _processor(text=prompt, images=image, return_tensors="pt").to(device, torch_dtype)

    generated_ids = _model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        do_sample=False,
        num_beams=3,
    )
    generated_text = _processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = _processor.post_process_generation(generated_text, task="<OPEN_VOCABULARY_DETECTION>", image_size=(image.width, image.height))
    return parsed_answer["<OPEN_VOCABULARY_DETECTION>"]