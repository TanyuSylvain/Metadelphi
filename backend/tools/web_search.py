"""
Web Search Tool loader.

Supports two backends:
1. Tavily SDK (native) - when TAVILY_API_KEY is configured.
2. Configurable MCP servers - legacy Bailian/DashScope default servers or custom MCP_SERVERS.

The default backend is controlled by DEFAULT_SEARCH_ENGINE ("bailian" or "tavily").
The non-default backend is used as a fallback when the default is unavailable.
"""

import asyncio
import logging
from typing import List

from langchain_core.tools import BaseTool

from backend.config import settings
from backend.tools.tavily_tools import get_tavily_tools

logger = logging.getLogger(__name__)

# Module-level cache for loaded tools
_cached_tools: List[BaseTool] | None = None


def is_web_search_available() -> bool:
    """Check if web search is available (Tavily key or MCP servers configured)."""
    status = settings.get_search_engine_status()
    return status["configured"]


async def _load_mcp_tools() -> List[BaseTool]:
    """Load web search tools from configured MCP servers."""
    servers = settings.get_mcp_servers()
    if not servers:
        return []

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient

        all_tools = []

        # Connect to each configured MCP server sequentially with retry to avoid 429 rate limits
        for server in servers:
            server_name = server.get("name", "unnamed")
            server_url = server.get("url", "")
            transport = server.get("transport", "sse")
            api_key = server.get("api_key")
            custom_headers = server.get("headers", {})

            if not server_url:
                logger.warning(f"Skipping MCP server '{server_name}': no URL configured")
                continue

            # Build headers with authentication
            headers = dict(custom_headers)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            # Retry logic to handle transient failures
            for attempt in range(3):
                try:
                    client = MultiServerMCPClient(
                        {
                            server_name: {
                                "url": server_url,
                                "transport": transport,
                                "headers": headers,
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

            # Delay between servers to avoid rate limiting
            await asyncio.sleep(2)

        return all_tools

    except Exception as e:
        logger.error(f"Failed to load web search tools from MCP servers: {e}")
        return []


async def _load_tavily_tools() -> List[BaseTool]:
    """Load native Tavily SDK tools."""
    try:
        tools = get_tavily_tools()
        logger.info(f"Loaded {len(tools)} Tavily tools: {[t.name for t in tools]}")
        return tools
    except Exception as e:
        logger.error(f"Failed to load Tavily tools: {e}")
        return []


async def _load_engine_tools(engine: str) -> List[BaseTool]:
    """Load tools for a specific search engine."""
    if engine == "tavily":
        return await _load_tavily_tools()
    return await _load_mcp_tools()


async def get_web_search_tools() -> List[BaseTool]:
    """
    Get web search tools from the configured default engine, falling back to
    the other engine if the default is unavailable.

    Returns cached tools if already loaded. Returns empty list
    if no search backend is configured.

    Returns:
        List of LangChain tools for web search
    """
    global _cached_tools

    if _cached_tools is not None:
        return _cached_tools

    status = settings.get_search_engine_status()
    if not status["configured"]:
        logger.info("No search engine configured, web search unavailable")
        _cached_tools = []
        return _cached_tools

    default_engine = status["default"]
    fallback_engine = "bailian" if default_engine == "tavily" else "tavily"

    all_tools = []

    # Try default engine first
    if status["available"].get(default_engine, False):
        logger.info(f"Loading default search engine: {default_engine}")
        all_tools = await _load_engine_tools(default_engine)

    # Fall back to the other engine if default yielded nothing
    if not all_tools and status["available"].get(fallback_engine, False):
        logger.info(f"Falling back to search engine: {fallback_engine}")
        all_tools = await _load_engine_tools(fallback_engine)

    _cached_tools = all_tools
    logger.info(f"Total web search tools loaded: {len(_cached_tools)}")
    return _cached_tools


def clear_tool_cache():
    """Clear the cached tools to force reload on next call."""
    global _cached_tools
    _cached_tools = None
