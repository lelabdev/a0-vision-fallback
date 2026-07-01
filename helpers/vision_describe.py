"""
Vision Fallback helper: calls a dedicated vision model to describe images.
This is used when the main chat model doesn't support vision input.
"""

import base64
import hashlib
import mimetypes
import os
from pathlib import Path

import litellm

# Provider to .env variable mapping
_PROVIDER_ENV_KEYS = {
    "openrouter": "API_KEY_OPENROUTER",
    "ollama": "API_KEY_OLLAMA",
    "ollama_cloud": "API_KEY_OLLAMA_CLOUD",
    "openai": "API_KEY_OPENAI",
    "anthropic": "API_KEY_ANTHROPIC",
    "google": "API_KEY_GOOGLE",
    "groq": "API_KEY_GROQ",
    "xai": "API_KEY_XAI",
    "mistral": "API_KEY_MISTRAL",
    "deepseek": "API_KEY_DEEPSEEK",
    "venice": "API_KEY_VENICE",
    "sambanova": "API_KEY_SAMBANOVA",
    "huggingface": "API_KEY_HUGGINGFACE",
    "nebius": "API_KEY_NEBIUS",
    "moonshot": "API_KEY_MOONSHOT",
}


def _resolve_api_key_from_env(provider: str) -> str:
    """Try to resolve API key from Agent Zero .env variables."""
    env_var = _PROVIDER_ENV_KEYS.get(provider, "")
    if env_var:
        return os.environ.get(env_var, "")
    return ""

# Simple in-memory cache: {image_hash: description}
# Avoids re-calling the vision model for the same image in the same session
_description_cache: dict[str, str] = {}


def get_vision_config() -> dict:
    """Get the vision fallback plugin configuration."""
    from helpers.plugins import get_plugin_config
    cfg = get_plugin_config("a0_vision_fallback") or {}
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


def _hash_image(data_url: str) -> str:
    """Compute a hash of an image data URL for cache lookup."""
    return hashlib.md5(data_url.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    """Estimate token count for a text string (~4 chars per token)."""
    return max(1, len(text) // 4)


def image_to_data_url(image_path: str) -> str:
    """Convert a local image file or data URL to a data URL."""
    if image_path.startswith("data:"):
        return image_path

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
    Uses a simple hash-based cache to avoid duplicate API calls.

    Args:
        image_path: Path to the local image file or a data URL

    Returns:
        Text description of the image
    """
    # Convert to data URL first (needed for hashing and API call)
    data_url = image_to_data_url(image_path)

    # Check cache
    img_hash = _hash_image(data_url)
    if img_hash in _description_cache:
        return _description_cache[img_hash]

    model_cfg = get_vision_model_config()
    provider = model_cfg.get("provider", "openrouter")
    model_name = model_cfg.get("name", "google/gemini-2.5-flash")
    # Auto-resolve API key from plugin config, then from Agent Zero .env
    api_key = model_cfg.get("api_key", "") or _resolve_api_key_from_env(provider)
    api_base = model_cfg.get("api_base", "")
    prompt = get_prompt()

    # Build the LiteLLM model string and handle provider-specific settings
    # LiteLLM uses "ollama" prefix for both local and cloud Ollama
    if provider in ("ollama", "ollama_cloud"):
        litellm_model = f"ollama/{model_name}"
        if provider == "ollama_cloud" and not api_base:
            api_base = "https://ollama.com"
    elif provider not in ("openai", "azure"):
        litellm_model = f"{provider}/{model_name}"
    else:
        litellm_model = model_name

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
        description = response.choices[0].message.content.strip()
        # Cache the result
        _description_cache[img_hash] = description
        return description
    except Exception as e:
        return f"[Vision Fallback Error: Failed to describe image: {e}]"
