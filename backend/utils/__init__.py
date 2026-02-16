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

__all__ = [
    "TextProcessor",
    "json_converter",
    "JsonConverter",
    "extract_citations_from_result",
    "CITATION_SYSTEM_INSTRUCTION",
    "format_citations_metadata",
    "strip_citations_metadata",
]
