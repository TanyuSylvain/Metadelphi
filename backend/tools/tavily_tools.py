"""
Tavily web search tools implemented via the official tavily-python SDK.

Exposes Search, Extract, Crawl, and Map as LangChain-compatible tools.
The Tavily SDK is imported lazily so the dependency is only required when
TAVILY_API_KEY is configured.
"""

import logging
from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from backend.config import settings

logger = logging.getLogger(__name__)


def _get_tavily_client():
    """Return an AsyncTavilyClient if a key is configured."""
    api_key = settings.tavily_api_key
    if not api_key:
        return None
    try:
        from tavily import AsyncTavilyClient
        return AsyncTavilyClient(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Tavily client: {e}")
        return None


class TavilySearchInput(BaseModel):
    """Input schema for Tavily search."""
    query: str = Field(..., description="The search query.")
    search_depth: str = Field(
        default="advanced",
        description='Search depth: "basic" (faster, 1 credit) or "advanced" (higher quality, 2 credits).',
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of search results to return (1-20).",
    )
    include_domains: Optional[List[str]] = Field(
        default=None,
        description="Optional list of domains to include in the search.",
    )
    exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="Optional list of domains to exclude from the search.",
    )
    include_answer: bool = Field(
        default=False,
        description="Whether to include a short AI-generated answer in the response.",
    )
    include_raw_content: bool = Field(
        default=False,
        description="Whether to include the full raw page content for each result.",
    )
    include_images: bool = Field(
        default=False,
        description="Whether to include a list of images extracted from the search results.",
    )
    chunks_per_source: Optional[int] = Field(
        default=3,
        ge=0,
        le=3,
        description="Number of content chunks per source when using advanced search (0-3).",
    )


class TavilySearchTool(BaseTool):
    """Search the web using Tavily."""

    name: str = "tavily_search"
    description: str = (
        "Search the web for current information, news, documentation, and facts. "
        "Returns a list of results with titles, URLs, and relevant content snippets. "
        "Use this when you need to find information on the public web."
    )
    args_schema: Type[BaseModel] = TavilySearchInput

    async def _arun(
        self,
        query: str,
        search_depth: str = "advanced",
        max_results: int = 5,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
        chunks_per_source: Optional[int] = 3,
        **kwargs,
    ) -> str:
        client = _get_tavily_client()
        if client is None:
            return "Error: Tavily is not configured."
        try:
            response = await client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                include_answer=include_answer,
                include_raw_content=include_raw_content,
                include_images=include_images,
                chunks_per_source=chunks_per_source,
            )
            return _format_search_response(response)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return f"Error performing Tavily search: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Tavily tools are async-only.")


class TavilyExtractInput(BaseModel):
    """Input schema for Tavily extract."""
    urls: List[str] = Field(
        ...,
        description="List of URLs to extract content from.",
    )
    extract_depth: str = Field(
        default="basic",
        description='Extraction depth: "basic" or "advanced".',
    )
    include_images: bool = Field(
        default=False,
        description="Whether to include a list of images extracted from the URLs.",
    )


class TavilyExtractTool(BaseTool):
    """Extract clean content from specific URLs using Tavily."""

    name: str = "tavily_extract"
    description: str = (
        "Extract the main content from one or more specific URLs. "
        "Use this when you already have URLs (e.g., from search results) and need "
        "to read their content without visiting the page manually."
    )
    args_schema: Type[BaseModel] = TavilyExtractInput

    async def _arun(
        self,
        urls: List[str],
        extract_depth: str = "basic",
        include_images: bool = False,
        **kwargs,
    ) -> str:
        client = _get_tavily_client()
        if client is None:
            return "Error: Tavily is not configured."
        try:
            response = await client.extract(
                urls=urls,
                extract_depth=extract_depth,
                include_images=include_images,
            )
            return _format_extract_response(response)
        except Exception as e:
            logger.error(f"Tavily extract failed: {e}")
            return f"Error performing Tavily extract: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Tavily tools are async-only.")


class TavilyCrawlInput(BaseModel):
    """Input schema for Tavily crawl."""
    url: str = Field(
        ...,
        description="The starting URL to crawl.",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional natural-language instructions to guide the crawl.",
    )
    max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum crawl depth (1-5).",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of pages to crawl.",
    )


class TavilyCrawlTool(BaseTool):
    """Crawl a website starting from a URL using Tavily."""

    name: str = "tavily_crawl"
    description: str = (
        "Crawl a website starting from a given URL and extract content from multiple pages. "
        "Use this for exploring documentation sites, blogs, or other structured websites."
    )
    args_schema: Type[BaseModel] = TavilyCrawlInput

    async def _arun(
        self,
        url: str,
        instructions: Optional[str] = None,
        max_depth: int = 2,
        limit: int = 10,
        **kwargs,
    ) -> str:
        client = _get_tavily_client()
        if client is None:
            return "Error: Tavily is not configured."
        try:
            response = await client.crawl(
                url=url,
                instructions=instructions,
                max_depth=max_depth,
                limit=limit,
            )
            return _format_crawl_response(response)
        except Exception as e:
            logger.error(f"Tavily crawl failed: {e}")
            return f"Error performing Tavily crawl: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Tavily tools are async-only.")


class TavilyMapInput(BaseModel):
    """Input schema for Tavily map."""
    url: str = Field(
        ...,
        description="The root URL to map.",
    )
    instructions: Optional[str] = Field(
        default=None,
        description="Optional natural-language instructions to guide the mapping.",
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Maximum mapping depth (1-5).",
    )
    max_breadth: int = Field(
        default=20,
        ge=1,
        le=500,
        description="Maximum number of links to follow per level.",
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum total number of URLs to discover.",
    )


class TavilyMapTool(BaseTool):
    """Map/discover URLs on a website using Tavily."""

    name: str = "tavily_map"
    description: str = (
        "Discover all URLs on a website starting from a root URL. "
        "Use this to get a sitemap or find relevant pages before crawling or extracting content."
    )
    args_schema: Type[BaseModel] = TavilyMapInput

    async def _arun(
        self,
        url: str,
        instructions: Optional[str] = None,
        max_depth: int = 1,
        max_breadth: int = 20,
        limit: int = 50,
        **kwargs,
    ) -> str:
        client = _get_tavily_client()
        if client is None:
            return "Error: Tavily is not configured."
        try:
            response = await client.map(
                url=url,
                instructions=instructions,
                max_depth=max_depth,
                max_breadth=max_breadth,
                limit=limit,
            )
            return _format_map_response(response)
        except Exception as e:
            logger.error(f"Tavily map failed: {e}")
            return f"Error performing Tavily map: {e}"

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Tavily tools are async-only.")


def _format_search_response(response: dict) -> str:
    """Format a Tavily search response as Markdown."""
    lines = []
    query = response.get("query", "")
    if query:
        lines.append(f"Search results for: {query}\n")

    answer = response.get("answer")
    if answer:
        lines.append(f"**Answer:** {answer}\n")

    results = response.get("results", [])
    if not results:
        lines.append("No results found.")
        return "\n".join(lines)

    top_images = response.get("images", [])
    if top_images:
        lines.append("**Images:**")
        lines.extend(_format_image_list(top_images))
        lines.append("")

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")
        score = result.get("score")
        raw = result.get("raw_content", "")
        images = result.get("images", [])

        lines.append(f"{i}. [{title}]({url})")
        if score is not None:
            lines.append(f"   - Relevance: {score:.2f}")
        if content:
            lines.append(f"   - {content}")
        if raw:
            lines.append(f"   - Full content: {raw[:2000]}")
        if images:
            lines.append("   - Images:")
            for img in _format_image_list(images, indent="     "):
                lines.append(img)
        lines.append("")

    return "\n".join(lines)


def _format_extract_response(response: dict) -> str:
    """Format a Tavily extract response as Markdown."""
    lines = []
    results = response.get("results", [])
    failed = response.get("failed_results", [])

    if not results and not failed:
        return "No content extracted."

    for result in results:
        url = result.get("url", "")
        title = result.get("title", "Untitled")
        raw = result.get("raw_content", "")
        images = result.get("images", [])
        lines.append(f"## {title}")
        lines.append(f"URL: {url}\n")
        if raw:
            lines.append(raw)
        else:
            lines.append("No raw content available.")
        if images:
            lines.append("\n**Images:**")
            lines.extend(_format_image_list(images))
        lines.append("")

    if failed:
        lines.append("**Failed URLs:**")
        for item in failed:
            if isinstance(item, dict):
                lines.append(f"- {item.get('url', item)}")
            else:
                lines.append(f"- {item}")

    return "\n".join(lines)


def _format_image_list(images: list, indent: str = "") -> List[str]:
    """Format a list of Tavily image objects as Markdown lines."""
    lines = []
    for img in images:
        if isinstance(img, dict):
            url = img.get("url", "")
            description = img.get("description", "")
            if url and description:
                lines.append(f"{indent}- [{description}]({url})")
            elif url:
                lines.append(f"{indent}- ![image]({url})")
            elif description:
                lines.append(f"{indent}- {description}")
        elif isinstance(img, str):
            lines.append(f"{indent}- ![image]({img})")
    return lines


def _format_crawl_response(response: dict) -> str:
    """Format a Tavily crawl response as Markdown."""
    lines = []
    base_url = response.get("base_url", "")
    if base_url:
        lines.append(f"Crawl results for: {base_url}\n")

    results = response.get("results", [])
    if not results:
        lines.append("No pages crawled.")
        return "\n".join(lines)

    for i, result in enumerate(results, 1):
        url = result.get("url", "")
        raw = result.get("raw_content", "")
        lines.append(f"## Page {i}: {url}\n")
        if raw:
            lines.append(raw)
        else:
            lines.append("No content available.")
        lines.append("")

    return "\n".join(lines)


def _format_map_response(response: dict) -> str:
    """Format a Tavily map response as Markdown."""
    lines = []
    base_url = response.get("base_url", "")
    if base_url:
        lines.append(f"Discovered URLs on {base_url}:\n")

    results = response.get("results", [])
    if not results:
        lines.append("No URLs discovered.")
        return "\n".join(lines)

    for url in results:
        lines.append(f"- {url}")

    return "\n".join(lines)


def get_tavily_tools() -> List[BaseTool]:
    """Return the list of Tavily tools if configured and the SDK is importable."""
    if not settings.tavily_api_key:
        return []
    try:
        from tavily import AsyncTavilyClient
        # Verify the client can be instantiated (catches missing dependency / bad key format)
        AsyncTavilyClient(api_key=settings.tavily_api_key)
    except Exception as e:
        logger.error(f"Tavily SDK is not available or misconfigured: {e}")
        return []
    return [
        TavilySearchTool(),
        TavilyExtractTool(),
        TavilyCrawlTool(),
        TavilyMapTool(),
    ]
