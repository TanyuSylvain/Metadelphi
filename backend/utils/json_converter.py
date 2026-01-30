"""
JSON extraction and conversion utilities for LLM responses.

Handles JSON parsing from LLM responses, with fallback to using a lightweight
model (qwen-flash) for conversion when the source LLM has thinking mode enabled
(which is incompatible with JSON mode).

Usage:
    from backend.utils.json_converter import json_converter

    result = json_converter.extract(text, use_converter=True)
"""

import json
import re
import logging

from backend.providers import ProviderFactory

logger = logging.getLogger(__name__)


class JsonConverter:
    """
    JSON extraction and conversion for LLM responses (Singleton).

    Provides methods to extract JSON from text responses, with optional fallback
    to using a lightweight LLM (qwen-flash) for conversion when direct parsing fails.
    This is particularly useful when the source LLM has thinking mode enabled,
    which is incompatible with JSON mode.
    """

    _instance = None

    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._converter_llm = None
        return cls._instance

    def _get_converter_llm(self):
        """Get or create a cached JSON converter LLM (qwen-flash with JSON mode)."""
        if self._converter_llm is None:
            self._converter_llm = ProviderFactory.create_llm(
                model_id="qwen-flash",
                provider_name="qwen",
                temperature=0,
                json_mode=True
            )
            logger.info("Created JSON converter LLM: qwen-flash")
        return self._converter_llm

    def _convert_with_llm(self, text: str) -> dict:
        """
        Convert text response to JSON using qwen-flash model.

        Args:
            text: Raw text response from LLM

        Returns:
            Parsed JSON dict
        """
        converter = self._get_converter_llm()

        prompt = f"""Extract and convert the following text into a valid JSON object.
If the text already contains JSON (possibly in code blocks), extract and return it.
If not, convert the content into the appropriate JSON structure.

Text to convert:
{text}

Return ONLY the JSON object, no explanations."""

        response = converter.invoke([{"role": "user", "content": prompt}])
        content = response.content if hasattr(response, 'content') else str(response)

        # Extract text content if it's a list
        if isinstance(content, list):
            content = ''.join(
                block.get('text', '') if isinstance(block, dict) else str(block)
                for block in content
            )

        # Try to parse JSON from response
        try:
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
            if json_match:
                return json.loads(json_match.group(1).strip())
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON converter failed to parse response: {e}")
            return {"error": "Failed to convert to JSON", "raw": content}

    def extract(self, text: str, use_converter: bool = False) -> dict:
        """
        Extract JSON from LLM response, handling markdown code blocks.

        Args:
            text: Raw text response from LLM
            use_converter: If True, use qwen-flash to convert text to JSON when
                          direct parsing fails. Use this when the source LLM has
                          thinking mode enabled (which is incompatible with JSON mode).

        Returns:
            Parsed JSON dict. Returns {"error": ..., "raw": ...} if parsing fails.
        """
        # First, try direct JSON extraction
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            json_str = text.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            if not use_converter:
                logger.warning(f"Failed to parse JSON: {e}")
                return {"error": "Failed to parse response", "raw": text}

            # Use qwen-flash JSON converter as fallback
            logger.info("Using JSON converter for thinking mode response")
            return self._convert_with_llm(text)


# Module-level singleton instance for convenient import
json_converter = JsonConverter()
