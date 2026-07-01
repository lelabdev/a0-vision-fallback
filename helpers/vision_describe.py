"""
Vision Fallback helper: calls a dedicated vision model to describe images.
This is used when the main chat model doesn't support vision input.
"""

import base64
import mimetypes
from pathlib import Path

import litellm
from helpers import settings


def get_vision_config() -> dict:
    """Get the vision fallback plugin configuration."""
    from helpers.plugins import get_plugin_config
    cfg = get_plugin_config("vision_fallback") or {}
    return cfg


def is_enabled() -> bool:
    """Check if vision fallback is enabled."""
    cfg = get_vision_config()
    return cfg.get("enabled", True)


def get_vision_model_config() -> dict:
    """Get the configured vision model details."""
    cfg = get_vision_config()
    return cfg.get("vision_model", {})


def get_prompt() -> str:
    """Get the prompt used for image description."""
    cfg = get_vision_config()
    return cfg.get(
        "prompt",
        "Describe this image in detail. Include objects, colors, text, layout, and any notable features. Be concise but thorough."
    )


def image_to_data_url(image_path: str) -> str:
    """Convert a local image file to a data URL."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"

    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


async def describe_image(image_path: str) -> str:
    """
    Send an image to the vision model and get a text description.

    Args:
        image_path: Path to the local image file

    Returns:
        Text description of the image
    """
    model_cfg = get_vision_model_config()
    provider = model_cfg.get("provider", "openrouter")
    model_name = model_cfg.get("name", "google/gemini-2.5-flash")
    api_key = model_cfg.get("api_key", "")
    api_base = model_cfg.get("api_base", "")
    prompt = get_prompt()

    # Build the LiteLLM model string
    litellm_model = f"{provider}/{model_name}" if provider not in ("openai", "azure") else model_name

    # Convert image to data URL
    if image_path.startswith("data:"):
        data_url = image_path
    else:
        data_url = image_to_data_url(image_path)

    # Build messages for the vision model
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    ]

    # Prepare kwargs
    kwargs = {
        "model": litellm_model,
        "messages": messages,
        "stream": False,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    try:
        response = await litellm.acompletion(**kwargs)
        description = response.choices[0].message.content
        return description.strip()
    except Exception as e:
        return f"[Vision Fallback Error: Failed to describe image: {e}]"
