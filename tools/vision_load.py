"""
Vision Fallback: Custom vision_load tool.

Overrides the default vision_load tool to intercept images when the chat model
doesn't support vision. Instead of sending raw image blocks (which causes API
errors), it calls a dedicated vision model to describe each image and inserts
the text description into the conversation.
"""

from helpers.print_style import PrintStyle
from helpers.tool import Tool, Response
from helpers import runtime, files, plugins, ephemeral_images, images, chat_media, history
from mimetypes import guess_type

from usr.plugins.vision_fallback.helpers.vision_describe import (
    is_enabled as fallback_is_enabled,
    describe_image,
)

TOKENS_ESTIMATE = 1500


class VisionLoad(Tool):
    async def execute(self, paths: list[str] = [], **kwargs) -> Response:
        self.images_dict = {}
        self.loaded_paths: list[str] = []
        self.skipped_paths: list[str] = []

        max_embeds = self._get_max_embeds()
        requested = [
            (str(path or "").strip(), self._display_input_path(str(path or "").strip(), idx + 1))
            for idx, path in enumerate(paths)
        ]
        limited_paths = requested if max_embeds <= 0 else requested[-max_embeds:]
        self.skipped_paths = (
            [display for _, display in requested[:-max_embeds]]
            if max_embeds > 0 and len(requested) > max_embeds
            else []
        )

        for idx, (path, display_path) in enumerate(limited_paths):
            if not path:
                continue
            if ephemeral_images.is_ref(path):
                image = ephemeral_images.consume_image(
                    path,
                    context_id=self._context_id(),
                )
                if image is None:
                    continue
                display = image.display_name or display_path
                stored_ref = self._store_ephemeral_image(image)
                if stored_ref:
                    self.images_dict[display] = stored_ref
                    self.loaded_paths.append(display)
                continue
            if self._is_data_image_url(path):
                stored_ref = self._store_data_url(path, preferred_name=f"vision-load-{idx + 1}.png")
                if stored_ref:
                    self.images_dict[display_path] = stored_ref
                    self.loaded_paths.append(display_path)
                continue
            if not await runtime.call_development_function(files.exists, str(path)):
                continue

            if path not in self.images_dict:
                mime_type, _ = guess_type(str(path))
                if mime_type and mime_type.startswith("image/"):
                    try:
                        stored_ref = self._store_local_image(path, preferred_name=files.basename(path))
                        self.images_dict[display_path] = stored_ref
                        self.loaded_paths.append(display_path)
                    except (FileNotFoundError, OSError, ValueError):
                        continue

        return Response(message="dummy", break_loop=False)

    def _get_max_embeds(self) -> int:
        cfg = plugins.get_plugin_config("_model_config", agent=self.agent) or {}
        chat_cfg = cfg.get("chat_model", {})
        max_embeds = chat_cfg.get("max_embeds", 10)
        return int(max_embeds or 0)

    def _context_id(self) -> str:
        return str(getattr(getattr(self.agent, "context", None), "id", "") or "").strip()

    def _chat_model_supports_vision(self) -> bool:
        """Check if the current chat model supports vision."""
        cfg = plugins.get_plugin_config("_model_config", agent=self.agent) or {}
        chat_cfg = cfg.get("chat_model", {})
        return bool(chat_cfg.get("vision", False))

    def _store_ephemeral_image(self, image: ephemeral_images.EphemeralImage) -> str:
        context_id = self._context_id()
        if not context_id:
            return image.data_url
        source = chat_media.infer_source(image.ref, image.display_name)
        category = chat_media.category_for_source(source)
        saved = chat_media.save_image_base64(
            context_id=context_id,
            data=image.data,
            mime_type=image.mime,
            category=category,
            source=source,
            preferred_name=image.display_name,
        )
        return saved.a0_path

    def _store_data_url(self, data_url: str, *, preferred_name: str = "") -> str:
        context_id = self._context_id()
        if not context_id:
            return data_url
        source = chat_media.infer_source(data_url, preferred_name)
        category = chat_media.category_for_source(source)
        saved = chat_media.save_image_data_url(
            context_id=context_id,
            data_url=data_url,
            category=category,
            source=source,
            preferred_name=preferred_name,
        )
        return saved.a0_path

    def _store_local_image(self, path: str, *, preferred_name: str = "") -> str:
        context_id = self._context_id()
        if not context_id:
            return images.to_data_url(path)
        return chat_media.materialize_image_ref(
            context_id=context_id,
            url=path,
            source=chat_media.infer_source(path, preferred_name),
            preferred_name=preferred_name,
        )

    @staticmethod
    def _is_data_image_url(value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized.startswith("data:image/") and ";base64," in normalized

    @classmethod
    def _display_input_path(cls, value: str, index: int) -> str:
        if ephemeral_images.is_ref(value):
            return ephemeral_images.display_ref(value)
        if cls._is_data_image_url(value):
            prefix = value.split(",", 1)[0]
            return f"{prefix},<ephemeral-image-{index}>"
        return value

    def _resolve_image_path_for_vision(self, stored_ref: str) -> str:
        """Resolve a stored image reference to a path/data_url usable by the vision model."""
        if stored_ref.startswith("data:"):
            return stored_ref
        # Try to resolve local file path
        try:
            from helpers import files as files_helper
            # Handle a0:// protocol paths
            if stored_ref.startswith("a0://"):
                rel = stored_ref[5:]
                return files_helper.get_abs_path(rel)
            return stored_ref
        except Exception:
            return stored_ref

    async def after_execution(self, response: Response, **kwargs):
        loaded_count = len(self.loaded_paths)
        skipped_count = len(self.skipped_paths)
        loaded_summary = "\n".join(self.loaded_paths) if self.loaded_paths else "none"
        skipped_summary = "\n".join(self.skipped_paths) if self.skipped_paths else "none"
        summary = (
            f"Loaded images: {loaded_count}\n"
            f"Loaded images:\n{loaded_summary}\n\n"
            f"Skipped images: {skipped_count}\n"
            f"Skipped images (max {self._get_max_embeds()} loaded at a time according to model configuration):\n{skipped_summary}"
        )

        if not self.images_dict:
            self.agent.hist_add_tool_result(
                self.name, summary if self.skipped_paths else "No images processed",
                id=self.log.id if self.log else "",
            )
            message = (
                "No images processed"
                if not self.images_dict and not self.skipped_paths
                else f"{loaded_count} images loaded, {skipped_count} skipped"
            )
            PrintStyle(
                font_color="#1B4F72", background_color="white", padding=True, bold=True
            ).print(f"{self.agent.agent_name}: Response from tool '{self.name}'")
            PrintStyle(font_color="#85C1E9").print(message)
            self.log.update(result=message)
            return

        # Check if we need to use fallback
        use_fallback = (
            fallback_is_enabled()
            and not self._chat_model_supports_vision()
        )

        if use_fallback:
            # Fallback mode: describe each image with the vision model
            descriptions = []
            for display_path, image_ref in self.images_dict.items():
                try:
                    resolved = self._resolve_image_path_for_vision(image_ref)
                    PrintStyle(font_color="#8E44AD").print(
                        f"[Vision Fallback] Describing image: {display_path}"
                    )
                    description = await describe_image(resolved)
                    descriptions.append(f"**Image: {display_path}**\n{description}")
                except Exception as e:
                    descriptions.append(f"**Image: {display_path}**\n[Error describing image: {e}]")

            # Add descriptions as text in the conversation
            combined_text = "\n\n---\n\n".join(descriptions)
            fallback_summary = (
                f"{summary}\n\n"
                f"[Vision Fallback] The chat model doesn't support vision. "
                f"Images were described by a dedicated vision model:\n\n{combined_text}"
            )

            self.agent.hist_add_tool_result(
                self.name, fallback_summary, id=self.log.id if self.log else "",
            )

            msg = history.RawMessage(
                raw_content=[{"type": "text", "text": combined_text}],
                preview="<Vision fallback image descriptions>",
            )
            self.agent.hist_add_message(False, content=msg, tokens=500 * len(descriptions))

            message = f"{loaded_count} images described via vision fallback, {skipped_count} skipped"
        else:
            # Normal mode: send raw images to the chat model
            self.agent.hist_add_tool_result(
                self.name, summary, id=self.log.id if self.log else "",
            )
            content = []
            for path, image_path in self.images_dict.items():
                if image_path:
                    content.append(
                        {"type": "image_url", "image_url": {"url": image_path}}
                    )
                else:
                    content.append(
                        {"type": "text", "text": "Error processing image " + path}
                    )
            msg = history.RawMessage(
                raw_content=content, preview="<Image attachments loaded by path>",
            )
            self.agent.hist_add_message(
                False, content=msg, tokens=TOKENS_ESTIMATE * len(content)
            )
            message = (
                "No images processed"
                if not self.images_dict and not self.skipped_paths
                else f"{loaded_count} images loaded, {skipped_count} skipped"
            )

        PrintStyle(
            font_color="#1B4F72", background_color="white", padding=True, bold=True
        ).print(f"{self.agent.agent_name}: Response from tool '{self.name}'")
        PrintStyle(font_color="#85C1E9").print(message)
        self.log.update(result=message)
