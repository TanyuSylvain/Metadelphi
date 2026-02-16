"""
Web Search Tool via Alibaba DASHSCOPE MCP Server.

Lazy-loads web search tools from the DASHSCOPE MCP server using langchain-mcp-adapters.
Returns empty list if IQS_API_KEY is not configured (graceful degradation).
"""

import logging
from typing import List

from langchain_core.tools import BaseTool

from backend.config import settings

logger = logging.getLogger(__name__)

# Module-level cache for loaded tools
_cached_tools: List[BaseTool] | None = None


def is_web_search_available() -> bool:
    """Check if web search is available (DASHSCOPE API key configured)."""
    return bool(settings.dashscope_api_key)


async def get_web_search_tools() -> List[BaseTool]:
    """
    Get web search tools from the DASHSCOPE MCP server.

    Returns cached tools if already loaded. Returns empty list
    if DASHSCOPE_API_KEY is not configured.

    Returns:
        List of LangChain tools for web search
    """
    global _cached_tools

    if _cached_tools is not None:
        return _cached_tools

    if not settings.dashscope_api_key:
        logger.info("DASHSCOPE_API_KEY not configured, web search unavailable")
        _cached_tools = []
        return _cached_tools

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        client = MultiServerMCPClient(
            {
                "web-search": {
                    "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse",
                    "transport": "sse",
                    "headers": {
                        "Authorization": f"Bearer {settings.dashscope_api_key}"
                    },
                }
            }
        )

        tools = await client.get_tools()
        _cached_tools = tools
        logger.info(f"Loaded {len(tools)} web search tools from DASHSCOPE MCP: {[t.name for t in tools]}")
        return _cached_tools

    except Exception as e:
        logger.error(f"Failed to load web search tools from DASHSCOPE MCP: {e}")
        _cached_tools = []
        return _cached_tools
