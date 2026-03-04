"""
Web Search Tool via Configurable MCP Servers.

Lazy-loads web search tools from configured MCP servers using langchain-mcp-adapters.
Supports multi-server configuration via MCP_SERVERS env var or falls back to legacy
DASHSCOPE default servers. Returns empty list if no servers are configured.
"""

import asyncio
import logging
from typing import List

from langchain_core.tools import BaseTool

from backend.config import settings

logger = logging.getLogger(__name__)

# Module-level cache for loaded tools
_cached_tools: List[BaseTool] | None = None


def is_web_search_available() -> bool:
    """Check if web search is available (MCP servers configured)."""
    servers = settings.get_mcp_servers()
    return bool(servers)


async def get_web_search_tools() -> List[BaseTool]:
    """
    Get web search tools from configured MCP servers.

    Returns cached tools if already loaded. Returns empty list
    if no MCP servers are configured.

    Returns:
        List of LangChain tools for web search
    """
    global _cached_tools

    if _cached_tools is not None:
        return _cached_tools

    servers = settings.get_mcp_servers()
    if not servers:
        logger.info("No MCP servers configured, web search unavailable")
        _cached_tools = []
        return _cached_tools

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

        _cached_tools = all_tools
        logger.info(f"Total MCP tools loaded: {len(_cached_tools)}")
        return _cached_tools

    except Exception as e:
        logger.error(f"Failed to load web search tools from MCP servers: {e}")
        _cached_tools = []
        return _cached_tools


def clear_tool_cache():
    """Clear the cached tools to force reload on next call."""
    global _cached_tools
    _cached_tools = None
