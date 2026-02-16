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
        import asyncio
        from langchain_mcp_adapters.client import MultiServerMCPClient

        auth_header = {"Authorization": f"Bearer {settings.dashscope_api_key}"}
        all_tools = []

        # Connect to each Bailian MCP server sequentially with retry to avoid 429 rate limits
        for server_name, server_url in [
            ("web-search", "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse"),
            ("web-parser", "https://dashscope.aliyuncs.com/api/v1/mcps/WebParser/sse"),
        ]:
            for attempt in range(3):
                try:
                    client = MultiServerMCPClient(
                        {
                            server_name: {
                                "url": server_url,
                                "transport": "sse",
                                "headers": auth_header,
                            }
                        }
                    )
                    tools = await client.get_tools()
                    all_tools.extend(tools)
                    logger.info(f"Loaded {len(tools)} tools from {server_name}: {[t.name for t in tools]}")
                    break
                except Exception as e:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Attempt {attempt + 1} failed for {server_name}: {e}, retrying in {wait}s")
                    await asyncio.sleep(wait)
            else:
                logger.error(f"Failed to load tools from {server_name} after 3 attempts")
            await asyncio.sleep(2)

        _cached_tools = all_tools
        logger.info(f"Total Bailian MCP tools loaded: {len(_cached_tools)}")
        return _cached_tools

    except Exception as e:
        logger.error(f"Failed to load web search tools from DASHSCOPE MCP: {e}")
        _cached_tools = []
        return _cached_tools
