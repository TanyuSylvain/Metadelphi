"""
Citation utilities for web search results.

Provides extraction, formatting, and stripping of citation metadata
used by both simple chat and coworking agent modes.
"""

import re
import json
from typing import List, Dict


CITATION_SYSTEM_INSTRUCTION = (
    "When using information from web search results, you MUST cite your sources "
    "using numbered markers like [1], [2], etc. in your response text. "
    "Place the citation marker immediately after the relevant claim or sentence. "
    "Each number should correspond to the order in which sources appear in the search results."
)

# Patterns for extracting URLs from tool result text
_MARKDOWN_LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)')
_PLAIN_URL_RE = re.compile(r'(?<!\()(https?://[^\s\)\]>]+)')

# Delimiter pattern for citation metadata in streaming responses
_CITATIONS_DELIMITER_RE = re.compile(
    r'\n?\n?<!--CITATIONS_JSON(.+?)CITATIONS_JSON-->',
    re.DOTALL
)


def extract_citations_from_result(
    result_text: str,
    existing_citations: List[Dict]
) -> List[Dict]:
    """
    Parse tool result text for URLs and add them to the citations list.

    Extracts markdown links [title](url) and plain URLs, deduplicates
    by URL, and assigns sequential indices.

    Args:
        result_text: Raw text output from a search tool
        existing_citations: Mutable list to append new citations to

    Returns:
        The same existing_citations list (mutated in-place)
    """
    seen_urls = {c["url"] for c in existing_citations}

    # Extract markdown links first (higher quality — has title)
    for title, url in _MARKDOWN_LINK_RE.findall(result_text):
        url = url.rstrip('.,;:')
        if url not in seen_urls:
            existing_citations.append({
                "index": len(existing_citations) + 1,
                "url": url,
                "title": title.strip()
            })
            seen_urls.add(url)

    # Extract plain URLs as fallback
    for url in _PLAIN_URL_RE.findall(result_text):
        url = url.rstrip('.,;:')
        if url not in seen_urls:
            # Use domain as fallback title
            domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
            existing_citations.append({
                "index": len(existing_citations) + 1,
                "url": url,
                "title": domain
            })
            seen_urls.add(url)

    return existing_citations


def format_citations_metadata(citations: List[Dict]) -> str:
    """
    Format citations list as an HTML-comment delimiter for simple chat streaming.

    The delimiter is appended to the streamed response and parsed by the frontend.

    Args:
        citations: List of citation dicts with index, url, title

    Returns:
        Delimiter string like '\\n\\n<!--CITATIONS_JSON[...]CITATIONS_JSON-->'
    """
    return f"\n\n<!--CITATIONS_JSON{json.dumps(citations)}CITATIONS_JSON-->"


def strip_citations_metadata(text: str) -> str:
    """
    Remove citation metadata delimiter from text.

    Used before storing responses in the database so the delimiter
    doesn't persist in conversation history.

    Args:
        text: Response text potentially containing citation delimiter

    Returns:
        Cleaned text with delimiter removed
    """
    return _CITATIONS_DELIMITER_RE.sub('', text)
