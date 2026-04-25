"""
Centralized configuration management for the Metadelphi application.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["*"]

    # Model Configuration
    default_model: str = "mistral"
    model_temperature: float = 0.7

    # Provider API Keys
    mistral_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    glm_api_key: Optional[str] = None
    zhipuai_api_key: Optional[str] = None
    minimax_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Tool API Keys
    dashscope_api_key: Optional[str] = None

    # Provider Base URLs
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"

    # MCP Server Configuration (JSON string for multi-server config)
    mcp_servers_config: Optional[str] = None

    # Legacy MCP configuration (for backward compatibility)
    web_search_mcp_url: Optional[str] = None
    web_parser_mcp_url: Optional[str] = None
    mcp_transport_type: str = "sse"

    # Tool Execution
    max_tool_concurrency: int = 5

    # Storage Configuration
    storage_backend: str = "sqlite"  # Options: memory, sqlite, redis
    database_url: Optional[str] = "conversations.db"
    redis_url: Optional[str] = None

    # Multi-Agent Configuration
    multi_agent_max_iterations: int = 3
    multi_agent_score_threshold: float = 80.0
    multi_agent_session_timeout: int = 600  # seconds

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        key_map = {
            "mistral": self.mistral_api_key,
            "qwen": self.qwen_api_key or self.dashscope_api_key,
            "glm": self.glm_api_key or self.zhipuai_api_key,
            "minimax": self.minimax_api_key,
            "deepseek": self.deepseek_api_key,
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "gemini_image": self.gemini_api_key,
            "openai_image": self.openai_api_key,
        }
        return key_map.get(provider)

    def get_base_url(self, provider: str) -> Optional[str]:
        """Get base URL for a specific provider."""
        url_map = {
            "qwen": self.qwen_base_url,
            "glm": self.glm_base_url,
            "minimax": self.minimax_base_url,
            "deepseek": self.deepseek_base_url,
            "openai": self.openai_base_url,
            "gemini": self.gemini_base_url,
            "gemini_image": self.gemini_base_url,
            "openai_image": self.openai_base_url,
        }
        return url_map.get(provider)

    def _parse_mcp_servers(self) -> List[Dict[str, Any]]:
        """
        Parse MCP server configuration from JSON string or fall back to legacy config.

        Returns:
            List of server configs with: name, url, transport, api_key (resolved)
        """
        servers = []

        # Option 1: Parse from JSON config string
        if self.mcp_servers_config:
            try:
                config_list = json.loads(self.mcp_servers_config)
                for server in config_list:
                    # Resolve API key from env var if specified
                    api_key = None
                    api_key_env = server.get("api_key_env")
                    if api_key_env:
                        api_key = os.environ.get(api_key_env)
                    elif server.get("api_key"):
                        api_key = server["api_key"]

                    servers.append({
                        "name": server.get("name", "unnamed"),
                        "url": server.get("url", ""),
                        "transport": server.get("transport", "sse"),
                        "api_key": api_key,
                        "headers": server.get("headers", {})
                    })
                logger.info(f"Parsed {len(servers)} MCP servers from MCP_SERVERS config")
                return servers
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse MCP_SERVERS JSON: {e}")

        # Option 2: Legacy single-server config from individual env vars
        if self.dashscope_api_key:
            # Use default Bailian MCP servers
            if self.web_search_mcp_url:
                servers.append({
                    "name": "web-search",
                    "url": self.web_search_mcp_url,
                    "transport": self.mcp_transport_type,
                    "api_key": self.dashscope_api_key,
                    "headers": {}
                })
            else:
                servers.append({
                    "name": "web-search",
                    "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse",
                    "transport": "sse",
                    "api_key": self.dashscope_api_key,
                    "headers": {}
                })

            if self.web_parser_mcp_url:
                servers.append({
                    "name": "web-parser",
                    "url": self.web_parser_mcp_url,
                    "transport": self.mcp_transport_type,
                    "api_key": self.dashscope_api_key,
                    "headers": {}
                })
            else:
                servers.append({
                    "name": "web-parser",
                    "url": "https://dashscope.aliyuncs.com/api/v1/mcps/WebParser/sse",
                    "transport": "sse",
                    "api_key": self.dashscope_api_key,
                    "headers": {}
                })
            logger.info(f"Using legacy MCP config with {len(servers)} default Bailian servers")

        return servers

    def get_mcp_servers(self) -> List[Dict[str, Any]]:
        """
        Get configured MCP servers with resolved API keys.

        Returns:
            List of server configs ready for use with langchain-mcp-adapters
        """
        return self._parse_mcp_servers()


# Global settings instance
settings = Settings()
