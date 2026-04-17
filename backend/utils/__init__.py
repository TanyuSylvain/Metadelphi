"""
Utility modules for the backend.
"""

from backend.utils.text_processor import TextProcessor
from backend.utils.json_converter import json_converter, JsonConverter
from backend.utils.citation import (
    extract_citations_from_result,
    CITATION_SYSTEM_INSTRUCTION,
    format_citations_metadata,
    strip_citations_metadata,
)
from backend.utils.parallel_tools import (
    ToolCallSpec,
    ToolResult,
    execute_single_tool,
    execute_tools_parallel,
    create_tool_messages,
)
from backend.utils.errors import sanitize_error_message, DEFAULT_UPSTREAM_ERROR_MESSAGE

__all__ = [
    "TextProcessor",
    "json_converter",
    "JsonConverter",
    "extract_citations_from_result",
    "CITATION_SYSTEM_INSTRUCTION",
    "format_citations_metadata",
    "strip_citations_metadata",
    "ToolCallSpec",
    "ToolResult",
    "execute_single_tool",
    "execute_tools_parallel",
    "create_tool_messages",
    "sanitize_error_message",
    "DEFAULT_UPSTREAM_ERROR_MESSAGE",
]
