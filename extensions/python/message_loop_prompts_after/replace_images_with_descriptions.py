"""
Vision Fallback extension: replace image_url blocks with text descriptions.

This hook runs after the message loop prompts are prepared, just before they
are sent to the LLM. It scans all messages for image_url content blocks.
If vision fallback is enabled, it sends each image to a dedicated vision model
and replaces the image with a text description.
"""

from __future__ import annotations

from agent import LoopData
from helpers.extension import Extension
from helpers.print_style import PrintStyle

from usr.plugins.a0_vision_fallback.helpers.vision_describe import (
    is_enabled as fallback_is_enabled,
    describe_image,
)


def _find_image_blocks(content):
    """Recursively find all image_url blocks in a message content."""
    found = []

    def _scan(obj):
        if isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, dict):
                    if item.get("type") == "image_url":
                        url_val = item.get("image_url", {}).get("url", "")
                        if url_val:
                            found.append((obj, i, url_val))
                _scan(item)
        elif isinstance(obj, dict):
            if "raw_content" in obj:
                _scan(obj["raw_content"])
            for v in obj.values():
                _scan(v)

    _scan(content)
    return found


class ReplaceImagesWithDescriptions(Extension):
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Skip if fallback is disabled
        if not fallback_is_enabled():
            return

        history_output = getattr(loop_data, "history_output", None)
        if not history_output:
            return

        total_images = 0

        for msg in history_output:
            content = msg.get("content")
            if content is None:
                continue

            image_blocks = _find_image_blocks(content)
            if not image_blocks:
                continue

            for parent, idx, image_url in image_blocks:
                total_images += 1
                try:
                    PrintStyle(font_color="#8E44AD").print(
                        f"[Vision Fallback] Describing image..."
                    )
                    description = await describe_image(image_url)
                    parent[idx] = {
                        "type": "text",
                        "text": f"[Image description: {description}]",
                    }
                except Exception as e:
                    PrintStyle(font_color="#E74C3C").print(
                        f"[Vision Fallback] Error: {e}"
                    )
                    parent[idx] = {
                        "type": "text",
                        "text": f"[Image could not be described: {e}]",
                    }

        if total_images > 0:
            PrintStyle(font_color="#27AE60").print(
                f"[Vision Fallback] Replaced {total_images} image(s) with text."
            )
