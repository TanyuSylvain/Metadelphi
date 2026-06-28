"""
OpenAI Image Generation provider implementation.

Uses the OpenAI-compatible /v1/images/generations and /v1/images/edits
endpoints to support gpt-image-2 and other OpenAI image models.
"""

import base64
import json
import logging
from typing import List, Dict, AsyncIterator, Optional

import httpx

from .base import BaseLLMProvider
from backend.utils.errors import sanitize_error_message

logger = logging.getLogger(__name__)

ASPECT_RATIO_TO_SIZE = {
    "1:1": "1024x1024",
    "16:9": "1536x864",
    "4:3": "1280x960",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
    "9:16": "864x1536",
    "21:9": "1792x768",
}


class OpenAIImageProvider(BaseLLMProvider):
    """OpenAI image generation provider using the /v1/images/generations endpoint."""

    provider_id = "openai"

    def get_provider_name(self) -> str:
        return "OpenAI Image"

    def supports_streaming(self) -> bool:
        return False

    def is_image_model(self, model_id: str) -> bool:
        for model in self.MODELS:
            if model["id"] == model_id:
                return model.get("is_image_model", False)
        return False

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, **kwargs):
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)
        return {
            "model": validated_model,
            "api_key": validated_key,
            "temperature": temperature,
            "base_url": kwargs.get("base_url"),
        }

    async def generate(
        self,
        messages: List[Dict],
        model_id: str,
        api_key: str,
        base_url: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        edit_source_image: Optional[Dict] = None,
    ) -> AsyncIterator[Dict]:
        """
        Invoke the image model via OpenAI images endpoint and yield
        SSE-ready event dicts.

        Yields dicts with type:
          - {"type": "image", "data": "<base64>", "mime_type": "image/png", "index": N}
          - {"type": "done"}
          - {"type": "error", "message": "..."}
        """
        base = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"

        # Extract prompt from the last user message
        prompt = ""
        for msg in reversed(messages):
            if isinstance(msg, dict):
                role = msg.get("role", "")
                if role == "user":
                    parts = msg.get("parts", [])
                    if parts and isinstance(parts[0], dict):
                        prompt = parts[0].get("text", "")
                    break
        if not prompt:
            prompt = messages[-1].get("parts", [{}])[0].get("text", "") if messages else ""

        size = ASPECT_RATIO_TO_SIZE.get(aspect_ratio or "1:1", "1024x1024")

        body = {
            "model": model_id,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        }

        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if edit_source_image:
                    endpoint = f"{base}/images/edits"
                    image_bytes = base64.b64decode(edit_source_image.get("data", ""))
                    mime_type = edit_source_image.get("mime_type", "image/png")
                    files = {
                        "image": ("source.png", image_bytes, mime_type),
                    }
                    response = await client.post(endpoint, data=body, files=files, headers=headers)
                else:
                    endpoint = f"{base}/images/generations"
                    response = await client.post(
                        endpoint,
                        json=body,
                        headers={**headers, "Content-Type": "application/json"},
                    )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI image API HTTP error: {e.response.text}")
            yield {
                "type": "error",
                "message": sanitize_error_message(e, default="Image request failed."),
            }
            return
        except Exception as e:
            logger.error(f"Image request error: {e}")
            yield {
                "type": "error",
                "message": sanitize_error_message(e, default="Image request failed."),
            }
            return

        images = data.get("data", [])
        if not images:
            yield {"type": "error", "message": "No images in response"}
            return

        for idx, img in enumerate(images):
            b64_data = img.get("b64_json", "")
            yield {
                "type": "image",
                "data": b64_data,
                "mime_type": "image/png",
                "index": idx,
            }

        yield {"type": "done"}

    @staticmethod
    def build_messages(history: List[Dict], new_message: str) -> List[Dict]:
        """
        Build messages list from stored conversation history.

        OpenAI images endpoint is single-prompt — only the current message
        is used for generation. History is included for storage consistency.
        """
        contents = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                try:
                    parsed = json.loads(content)
                    text = parsed.get("text", "")
                    if text:
                        contents.append({"role": "assistant", "parts": [{"text": text}]})
                except (json.JSONDecodeError, TypeError):
                    if content:
                        contents.append({"role": "assistant", "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": new_message}]})
        return contents
