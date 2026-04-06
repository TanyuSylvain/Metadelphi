"""
Google Gemini Image Generation provider implementation.

Uses the native langchain-google-genai SDK (not the OpenAI-compatible endpoint)
to support image output modality.
"""

import json
import base64
import logging
from typing import List, Dict, AsyncIterator

from langchain_google_genai import ChatGoogleGenerativeAI, Modality
from langchain_core.messages import HumanMessage, AIMessage

from .base import BaseLLMProvider

logger = logging.getLogger(__name__)


class GeminiImageProvider(BaseLLMProvider):
    """Google Gemini image generation provider using the native GenAI SDK."""

    MODELS = [
        {
            "id": "gemini-3-pro-image-preview",
            "name": "Gemini 3 Pro Image",
            "description": "Gemini 3 Pro with native image generation",
            "supports_thinking": False,
            "thinking_locked": False,
            "is_image_model": True,
        },
        {
            "id": "gemini-2.5-flash-image-preview",
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
        # Image generation is not streamable (returns full response at once)
        return False

    def is_image_model(self, model_id: str) -> bool:
        for model in self.MODELS:
            if model["id"] == model_id:
                return model.get("is_image_model", False)
        return False

    def initialize(self, model_id: str, api_key: str, temperature: float = 0.7, **kwargs):
        """Return a ChatGoogleGenerativeAI instance with image output enabled."""
        validated_key = self.validate_api_key(api_key)
        validated_model = self.validate_model_id(model_id)
        init_kwargs = dict(
            model=validated_model,
            google_api_key=validated_key,
            response_modalities=[Modality.TEXT, Modality.IMAGE],
            temperature=temperature,
        )
        # Pass custom base_url if provided (e.g. for proxy/custom endpoint)
        base_url = kwargs.get("base_url")
        if base_url:
            init_kwargs["base_url"] = base_url
        return ChatGoogleGenerativeAI(**init_kwargs)

    async def generate(
        self,
        messages: List,
        model_id: str,
        api_key: str,
        temperature: float = 0.7,
    ) -> AsyncIterator[Dict]:
        """
        Invoke the image model and yield SSE-ready event dicts.

        Yields dicts with type:
          - {"type": "text_chunk", "content": "..."}
          - {"type": "image", "data": "<base64>", "mime_type": "image/png", "index": N}
          - {"type": "done"}
          - {"type": "error", "message": "..."}
        """
        try:
            llm = self.initialize(model_id, api_key, temperature)
            response = await llm.ainvoke(messages)

            if isinstance(response.content, list):
                image_index = 0
                text_parts = []
                image_parts = []

                for item in response.content:
                    if isinstance(item, str) and item.strip():
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        # langchain-google-genai returns image as {"type": "image_url", "image_url": {"url": "data:..."}}
                        if "image_url" in item:
                            url = item["image_url"].get("url", "")
                            if "," in url:
                                b64_data = url.split(",", 1)[1]
                            else:
                                b64_data = url
                            image_parts.append({"data": b64_data, "mime_type": "image/png", "index": image_index})
                            image_index += 1
                        # Some versions return inline_data style
                        elif "inline_data" in item:
                            inline = item["inline_data"]
                            b64_data = inline.get("data", "")
                            if isinstance(b64_data, bytes):
                                b64_data = base64.b64encode(b64_data).decode()
                            image_parts.append({
                                "data": b64_data,
                                "mime_type": inline.get("mime_type", "image/png"),
                                "index": image_index,
                            })
                            image_index += 1

                # Yield text first
                for text in text_parts:
                    yield {"type": "text_chunk", "content": text}

                # Then yield images
                for img in image_parts:
                    yield {"type": "image", **img}

            elif isinstance(response.content, str) and response.content.strip():
                yield {"type": "text_chunk", "content": response.content}

        except Exception as e:
            logger.error(f"Image generation error: {e}")
            yield {"type": "error", "message": str(e)}
            return

        yield {"type": "done"}

    @staticmethod
    def build_messages(history: List[Dict], new_message: str) -> List:
        """
        Build a LangChain messages list from stored conversation history.

        For image assistant messages (stored as JSON), only the text part is
        included in history to keep context manageable.
        """
        messages = []
        for msg in history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                # Try to parse JSON image response — use only text for context
                try:
                    parsed = json.loads(content)
                    text = parsed.get("text", "")
                    if text:
                        messages.append(AIMessage(content=text))
                except (json.JSONDecodeError, TypeError):
                    if content:
                        messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=new_message))
        return messages
