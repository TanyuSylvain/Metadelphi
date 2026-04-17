"""
Error normalization helpers for user-facing API responses.
"""

from __future__ import annotations

import json
import re
from typing import Any


DEFAULT_UPSTREAM_ERROR_MESSAGE = "Upstream request failed."

_MESSAGE_PATTERNS = [
    re.compile(r'"message"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'"detail"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r"'message'\s*:\s*'([^']+)'", re.IGNORECASE),
    re.compile(r"'detail'\s*:\s*'([^']+)'", re.IGNORECASE),
]


def sanitize_error_message(error: Any, default: str = DEFAULT_UPSTREAM_ERROR_MESSAGE) -> str:
    """
    Return a short user-facing error message without leaking raw response bodies.
    """
    for candidate in _iter_error_candidates(error):
        message = _extract_message(candidate, default)
        if message:
            return message
    return default


def _iter_error_candidates(error: Any):
    response = getattr(error, "response", None)
    if response is not None:
        try:
            yield response.json()
        except Exception:
            pass

        text = getattr(response, "text", None)
        if text:
            yield text

        content = getattr(response, "content", None)
        if isinstance(content, bytes):
            yield content.decode("utf-8", errors="replace")

    for attr_name in ("body", "detail", "message"):
        value = getattr(error, attr_name, None)
        if value:
            yield value

    for arg in getattr(error, "args", ()):
        if arg:
            yield arg

    if error:
        yield str(error)


def _extract_message(value: Any, default: str) -> str | None:
    if value is None:
        return None

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    if isinstance(value, dict):
        for key in ("message", "detail", "error_description", "description", "title", "msg", "reason"):
            if key in value:
                message = _extract_message(value[key], default)
                if message:
                    return message

        for key in ("error", "errors"):
            if key in value:
                message = _extract_message(value[key], default)
                if message:
                    return message
        return None

    if isinstance(value, list):
        for item in value:
            message = _extract_message(item, default)
            if message:
                return message
        return None

    if not isinstance(value, str):
        value = str(value)

    text = value.strip()
    if not text:
        return None

    parsed = _try_parse_embedded_json(text)
    if parsed is not None:
        message = _extract_message(parsed, default)
        if message:
            return message

    for pattern in _MESSAGE_PATTERNS:
        match = pattern.search(text)
        if match:
            message = _clean_plain_message(match.group(1))
            if message:
                return message

    title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if title_match:
        message = _clean_plain_message(title_match.group(1))
        if message:
            return message

    text = re.sub(r"^[A-Za-z ]*error code:\s*\d+\s*-\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\d{3}\s+[A-Za-z ]+\s*:\s*", "", text)

    message = _clean_plain_message(text)
    if _looks_like_plain_message(message):
        return message

    return None


def _try_parse_embedded_json(text: str) -> Any | None:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except Exception:
            return None

    match = re.search(r"(\{.*\}|\[.*\])", stripped, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except Exception:
        return None


def _clean_plain_message(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text.strip("\"'")


def _looks_like_plain_message(text: str) -> bool:
    if not text or len(text) > 280:
        return False
    if "\n" in text:
        return False
    if any(token in text for token in ("{", "}", "[", "]", "<html", "<body", "</")):
        return False
    return True
