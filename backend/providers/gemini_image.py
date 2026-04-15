"""
Google Gemini Image Generation provider implementation.

Uses the native Gemini REST API (generateContent endpoint) to support
image output modality with aspect ratio control.
"""

import json
import logging
from typing import List, Dict, AsyncIterator, Optional

import httpx

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiImageProvider(BaseLLMProvider):
    """Google Gemini image generation provider using the native GenAI REST API."""

    MODELS = [
        {
            "id": "gemini-3.1-flash-image-preview",
            "name": "Gemini 3.1 Flash Image",
            "description": "Gemini 3.1 Flash with native image generation",
            "supports_thinking": False,
            "thinking_locked": False,
            "is_image_model": True,
        },
        {
            "id": "gemini-2.5-flash-image",
            "name": "Gemini 2.5 Flash Image",
            "description": "Gemini 2.5 Flash with native image generation",
            "supports_thinking": False,
            "thinking_locked": False,
            "is_image_model": True,
        },
    ]

    def get_available_models(self) -> List[Dict[str, str]]:
        return self.MODELS

    def get_provider_name(self) -> str:
        return "Google Gemini Image"

    def supports_streaming(self) -> bool:
        # Image generation returns a full response at once
        return False

    def is_image_model(self, model_id: str) -> bool:
        for model in self.MODELS:
            if model["id"] == model_id:
                return model.get("is_image_model", False)
        return False

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, **kwargs):
        """Store initialization config for later use."""
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)
        return {
            "model": validated_model,
            "api_key": validated_key,
            "temperature": temperature,
            "base_url": kwargs.get("base_url"),
        }

    @staticmethod
    def _resolve_native_base_url(base_url: Optional[str]) -> str:
        """Derive the native Gemini base URL from the configured base URL."""
        if not base_url:
            return "https://generativelanguage.googleapis.com/v1beta"
        if base_url.endswith("/v1beta/openai"):
            return base_url[: -len("/openai")]
        if base_url.endswith("/v1beta"):
            return base_url
        # For proxies like packyapi that serve native API under /v1beta
        return f"{base_url}/v1beta"

    async def generate(
        self,
        messages: List[Dict],
        model_id: str,
        api_key: str,
        base_url: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
    ) -> AsyncIterator[Dict]:
        """
        Invoke the image model via native Gemini generateContent and yield
        SSE-ready event dicts.

        Yields dicts with type:
          - {"type": "text_chunk", "content": "..."}
          - {"type": "image", "data": "<base64>", "mime_type": "image/png", "index": N}
          - {"type": "done"}
          - {"type": "error", "message": "..."}
        """
        native_base = self._resolve_native_base_url(base_url)
        endpoint = f"{native_base}/models/{model_id}:generateContent?key={api_key}"

        body = {
            "contents": messages,
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
            },
        }
        if aspect_ratio:
            body["generationConfig"]["imageConfig"] = {"aspectRatio": aspect_ratio}

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(endpoint, json=body)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini image API HTTP error: {e.response.text}")
            yield {"type": "error", "message": f"Gemini API error: {e.response.text}"}
            return
        except Exception as e:
            logger.error(f"Image generation error: {e}")
            yield {"type": "error", "message": str(e)}
            return

        candidates = data.get("candidates", [])
        if not candidates:
            yield {"type": "error", "message": "No candidates in Gemini response"}
            return

        parts = candidates[0].get("content", {}).get("parts", [])
        image_index = 0
        for part in parts:
            if "text" in part:
                yield {"type": "text_chunk", "content": part["text"]}
            elif "inlineData" in part:
                inline = part["inlineData"]
                mime_type = inline.get("mimeType", "image/png")
                b64_data = inline.get("data", "")
                yield {
                    "type": "image",
                    "data": b64_data,
                    "mime_type": mime_type,
                    "index": image_index,
                }
                image_index += 1

        yield {"type": "done"}

    @staticmethod
    def build_messages(history: List[Dict], new_message: str) -> List[Dict]:
        """
        Build a native Gemini contents list from stored conversation history.

        For image assistant messages (stored as JSON), only the text part is
        included in history to keep context manageable.
        """
        contents = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                contents.append({"role": "user", "parts": [{"text": content}]})
            elif role == "assistant":
                # Try to parse JSON image response — use only text for context
                try:
                    parsed = json.loads(content)
                    text = parsed.get("text", "")
                    if text:
                        contents.append({"role": "model", "parts": [{"text": text}]})
                except (json.JSONDecodeError, TypeError):
                    if content:
                        contents.append({"role": "model", "parts": [{"text": content}]})
        contents.append({"role": "user", "parts": [{"text": new_message}]})
        return contents
