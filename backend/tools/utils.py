"""
Utility helpers for tool-related presentation logic.
"""

import re
from urllib.parse import urlsplit


def shorten_tool_text(value, max_len: int = 80) -> str:
    """Normalize whitespace and truncate for inline tool status text."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def find_first_tool_string(args, keys) -> str:
    """Recursively find the first non-empty string for any of the given keys."""
    if isinstance(args, dict):
        for key in keys:
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in args.values():
            found = find_first_tool_string(value, keys)
            if found:
                return found
    elif isinstance(args, list):
        for item in args:
            found = find_first_tool_string(item, keys)
            if found:
                return found
    return ""


def classify_tool_name(tool_name: str) -> str:
    """Classify tool names into user-facing categories."""
    name = (tool_name or "").lower()
    if "search" in name:
        return "search"
    if "parse" in name or "parser" in name:
        return "parse"
    return "generic"


def format_tool_url_target(url: str) -> str:
    """Display URLs compactly in inline status lines."""
    parsed = urlsplit(url)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.rstrip("/")
        display = parsed.netloc + path
        if parsed.query:
            display += "?..."
        return shorten_tool_text(display, 70)
    return shorten_tool_text(url, 70)


def format_tool_start(tool_name: str, args: dict) -> str:
    """Build a concise inline status line before tool execution."""
    tool_kind = classify_tool_name(tool_name)
    if tool_kind == "search":
        query = find_first_tool_string(
            args,
            ["query", "q", "keyword", "keywords", "search_query", "question", "input"]
        )
        if query:
            return f'> Web search: "{shorten_tool_text(query, 90)}"'
        return "> Web search"

    if tool_kind == "parse":
        target = find_first_tool_string(
            args,
            ["url", "link", "uri", "page_url", "target_url", "webpage", "website"]
        )
        if target:
            return f"> Open page: {format_tool_url_target(target)}"
        return "> Open page"

    pretty_name = (tool_name or "tool").replace("_", " ").replace("-", " ").strip()
    return f"> Using tool: {shorten_tool_text(pretty_name, 60)}"


def format_tool_result(tool_name: str, args: dict, output: str, success: bool) -> str:
    """Build a concise inline status line after tool execution."""
    tool_kind = classify_tool_name(tool_name)
    if not success:
        return f"> Tool failed: {shorten_tool_text(output, 90) or 'unknown error'}"

    if tool_kind == "search":
        source_count = len(set(re.findall(r"https?://[^\s)>\"]+", output or "")))
        if source_count > 0:
            label = "source" if source_count == 1 else "sources"
            return f"> Search complete: found {source_count} {label}"
        return "> Search complete"

    if tool_kind == "parse":
        target = find_first_tool_string(
            args,
            ["url", "link", "uri", "page_url", "target_url", "webpage", "website"]
        )
        if target:
            return f"> Page parsed: {format_tool_url_target(target)}"
        return "> Page parsed"

    return f"> Tool complete: {shorten_tool_text(tool_name, 60)}"
