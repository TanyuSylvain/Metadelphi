"""
Centralized configuration management for the Metadelphi application.
"""

import os
import re
import json
import time
import logging
import threading
from pathlib import Path
from typing import ClassVar, Dict, Optional, List, Any
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Provider metadata for GUI configuration
    PROVIDERS: ClassVar[Dict[str, Dict[str, Any]]] = {
        'MISTRAL': {
            'name': 'Mistral AI',
            'key_env': 'MISTRAL_API_KEY',
            'base_url_env': None,
            'default_base_url': None,
            'console_url': 'https://console.mistral.ai/',
            'test_model': 'mistral-small-latest',
            'description': 'Mistral AI provides powerful language models'
        },
        'QWEN': {
            'name': 'Alibaba Qwen (DashScope)',
            'key_env': 'QWEN_API_KEY',
            'base_url_env': 'QWEN_BASE_URL',
            'default_base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'console_url': 'https://dashscope.aliyuncs.com/',
            'test_model': 'qwen3.5-flash',
            'description': 'Qwen models from Alibaba Cloud'
        },
        'GLM': {
            'name': 'Zhipu GLM',
            'key_env': 'GLM_API_KEY',
            'base_url_env': 'GLM_BASE_URL',
            'default_base_url': 'https://open.bigmodel.cn/api/paas/v4',
            'console_url': 'https://open.bigmodel.cn/',
            'test_model': 'glm-4.7',
            'description': 'GLM models from Zhipu AI'
        },
        'MINIMAX': {
            'name': 'MiniMax',
            'key_env': 'MINIMAX_API_KEY',
            'base_url_env': 'MINIMAX_BASE_URL',
            'default_base_url': 'https://api.minimaxi.com/v1',
            'console_url': 'https://www.minimaxi.com/',
            'test_model': 'MiniMax-M2.7-highspeed',
            'description': 'MiniMax AI platform'
        },
        'DEEPSEEK': {
            'name': 'DeepSeek',
            'key_env': 'DEEPSEEK_API_KEY',
            'base_url_env': 'DEEPSEEK_BASE_URL',
            'default_base_url': 'https://api.deepseek.com',
            'console_url': 'https://platform.deepseek.com/',
            'test_model': 'deepseek-v4-flash',
            'description': 'DeepSeek AI models'
        },
        'OPENAI': {
            'name': 'OpenAI / OpenAI-compatible',
            'key_env': 'OPENAI_API_KEY',
            'base_url_env': 'OPENAI_BASE_URL',
            'default_base_url': 'https://api.openai.com/v1',
            'console_url': 'https://platform.openai.com/api-keys',
            'test_model': 'gpt-5.4-mini',
            'description': 'OpenAI GPT models or compatible APIs'
        },
        'GEMINI': {
            'name': 'Google Gemini',
            'key_env': 'GEMINI_API_KEY',
            'base_url_env': 'GEMINI_BASE_URL',
            'default_base_url': 'https://generativelanguage.googleapis.com/v1beta/openai',
            'console_url': 'https://makersuite.google.com/app/apikey',
            'test_model': 'gemini-3-flash-preview',
            'description': 'Google Gemini models'
        },
        'DASHSCOPE': {
            'name': 'Web Search (DashScope MCP)',
            'key_env': 'DASHSCOPE_API_KEY',
            'base_url_env': None,
            'default_base_url': None,
            'console_url': 'https://bailian.console.aliyun.com/',
            'test_model': None,
            'description': 'DashScope API key for web search MCP tools'
        },
    }

    # Provider ID to settings attribute mapping
    _PROVIDER_KEY_ATTRS: ClassVar[Dict[str, str]] = {
        'MISTRAL': 'mistral_api_key',
        'QWEN': 'qwen_api_key',
        'GLM': 'glm_api_key',
        'MINIMAX': 'minimax_api_key',
        'DEEPSEEK': 'deepseek_api_key',
        'OPENAI': 'openai_api_key',
        'GEMINI': 'gemini_api_key',
        'DASHSCOPE': 'dashscope_api_key',
    }

    _PROVIDER_URL_ATTRS: ClassVar[Dict[str, str]] = {
        'QWEN': 'qwen_base_url',
        'GLM': 'glm_base_url',
        'MINIMAX': 'minimax_base_url',
        'DEEPSEEK': 'deepseek_base_url',
        'OPENAI': 'openai_base_url',
        'GEMINI': 'gemini_base_url',
    }

    _PROVIDER_NAME_TO_ID: ClassVar[Dict[str, str]] = {
        'mistral': 'MISTRAL',
        'qwen': 'QWEN',
        'glm': 'GLM',
        'minimax': 'MINIMAX',
        'deepseek': 'DEEPSEEK',
        'openai': 'OPENAI',
        'gemini': 'GEMINI',
        'gemini_image': 'GEMINI',
        'openai_image': 'OPENAI',
    }

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

    @staticmethod
    def mask_key(key: Optional[str]) -> Optional[str]:
        """Mask an API key, showing only the last 4 characters."""
        if not key or len(key) < 8:
            return None
        return "********" + key[-4:]

    def get_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Return current provider configurations with masked keys."""
        configs = {}
        for provider_id, meta in self.PROVIDERS.items():
            key_attr = self._PROVIDER_KEY_ATTRS.get(provider_id)
            raw_key = getattr(self, key_attr, None) if key_attr else None

            url_attr = self._PROVIDER_URL_ATTRS.get(provider_id)
            base_url = getattr(self, url_attr, None) if url_attr else None

            configs[provider_id] = {
                'api_key_masked': self.mask_key(raw_key),
                'api_key_set': bool(raw_key),
                'base_url': base_url,
                'has_base_url': url_attr is not None,
                'display_name': meta['name'],
                'console_url': meta['console_url'],
                'default_base_url': meta['default_base_url'],
                'test_model': meta['test_model'],
                'category': 'tool' if provider_id == 'DASHSCOPE' else 'llm',
            }
        return configs

    _update_lock: ClassVar[threading.Lock] = threading.Lock()

    def update_providers(self, updates: Dict[str, Dict[str, Optional[str]]]) -> List[str]:
        """Update provider settings in-memory, in os.environ, and persist to .env."""
        updated = []
        with self._update_lock:
            for provider_id, fields in updates.items():
                provider_id = provider_id.upper()
                if provider_id not in self.PROVIDERS:
                    continue

                # Update API key
                if 'api_key' in fields:
                    new_key = fields['api_key']
                    # Skip masked values, but do NOT skip the rest of this provider's fields
                    if not (new_key and new_key.startswith('*')):
                        key_attr = self._PROVIDER_KEY_ATTRS.get(provider_id)
                        if key_attr:
                            setattr(self, key_attr, new_key or None)
                            env_var = self.PROVIDERS[provider_id]['key_env']
                            if new_key:
                                os.environ[env_var] = new_key
                            elif env_var in os.environ:
                                del os.environ[env_var]
                            updated.append(provider_id)

                # Update base URL
                if 'base_url' in fields:
                    new_url = fields['base_url'] or None  # normalize empty string to None
                    url_attr = self._PROVIDER_URL_ATTRS.get(provider_id)
                    if url_attr and new_url is not None:
                        setattr(self, url_attr, new_url)
                        env_var = self.PROVIDERS[provider_id]['base_url_env']
                        if env_var:
                            os.environ[env_var] = new_url
                        if provider_id not in updated:
                            updated.append(provider_id)

            self._persist_to_env()

        return updated

    def _get_env_path(self) -> Path:
        """Get the path to the .env file."""
        return Path(__file__).parent.parent / ".env"

    def _persist_to_env(self) -> None:
        """Persist current settings to .env file, preserving comments and structure."""
        env_path = self._get_env_path()

        # Collect all known env var names and their current values
        known_vars = {}
        for provider_id, meta in self.PROVIDERS.items():
            key_env = meta['key_env']
            key_attr = self._PROVIDER_KEY_ATTRS.get(provider_id)
            if key_attr:
                val = getattr(self, key_attr, None)
                known_vars[key_env] = val

            url_env = meta.get('base_url_env')
            if url_env:
                url_attr = self._PROVIDER_URL_ATTRS.get(provider_id)
                if url_attr:
                    val = getattr(self, url_attr, None)
                    known_vars[url_env] = val

        # Read existing .env
        lines = []
        if env_path.exists():
            lines = env_path.read_text().splitlines(keepends=True)

        # Track which vars we've already updated
        updated_vars = set()
        new_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comments (but check commented-out vars)
            if not stripped or stripped.startswith('#'):
                # Check if this is a commented-out known var (e.g., "# GEMINI_API_KEY=...")
                if stripped.startswith('#'):
                    comment_content = stripped[1:].strip()
                    for var_name in known_vars:
                        if comment_content.startswith(f"{var_name}="):
                            # If we have a value for this var, uncomment it
                            val = known_vars[var_name]
                            if val is not None:
                                new_lines.append(f"{var_name}={val}\n")
                                updated_vars.add(var_name)
                                break
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                continue

            # Check if this line is a known var
            matched = False
            for var_name in known_vars:
                if stripped.startswith(f"{var_name}="):
                    val = known_vars[var_name]
                    if val is not None:
                        new_lines.append(f"{var_name}={val}\n")
                    else:
                        # Remove the line (don't append)
                        pass
                    updated_vars.add(var_name)
                    matched = True
                    break

            if not matched:
                new_lines.append(line)

        # Append any vars that weren't in the file
        for var_name, val in known_vars.items():
            if var_name not in updated_vars and val is not None:
                new_lines.append(f"{var_name}={val}\n")

        # Ensure file ends with a newline
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'

        # Atomic write: write to temp file then rename
        tmp_path = env_path.with_suffix('.env.tmp')
        tmp_path.write_text(''.join(new_lines))
        tmp_path.replace(env_path)
        logger.info(f"Persisted settings to {env_path}")

    def test_provider(self, provider_id: str) -> Dict[str, Any]:
        """Test a provider connection using its lightest model."""
        from backend.providers.factory import ProviderFactory

        provider_id = provider_id.upper()
        meta = self.PROVIDERS.get(provider_id)
        if not meta:
            return {'success': False, 'message': f'Unknown provider: {provider_id}', 'latency_ms': None}

        # Special case: DashScope - test MCP endpoint
        if provider_id == 'DASHSCOPE':
            key_attr = self._PROVIDER_KEY_ATTRS['DASHSCOPE']
            api_key = getattr(self, key_attr, None)
            if not api_key:
                return {'success': False, 'message': 'No API key configured', 'latency_ms': None}
            import httpx
            url = "https://dashscope.aliyuncs.com/api/v1/mcps/WebSearch/sse"
            try:
                start = time.time()
                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, headers={"Authorization": f"Bearer {api_key}"}, follow_redirects=True)
                latency = (time.time() - start) * 1000
                if resp.status_code < 400:
                    return {'success': True, 'message': f'Connected (HTTP {resp.status_code})', 'latency_ms': round(latency, 1)}
                else:
                    return {'success': False, 'message': f'HTTP {resp.status_code}: {resp.text[:200]}', 'latency_ms': round(latency, 1)}
            except Exception as e:
                return {'success': False, 'message': str(e)[:200], 'latency_ms': None}

        # LLM providers - create a minimal LLM and send a test prompt
        test_model = meta.get('test_model')
        if not test_model:
            return {'success': False, 'message': 'No test model available', 'latency_ms': None}

        # Map provider_id to provider name used by factory
        provider_name_map = {
            'MISTRAL': 'mistral', 'QWEN': 'qwen', 'GLM': 'glm',
            'MINIMAX': 'minimax', 'DEEPSEEK': 'deepseek',
            'OPENAI': 'openai', 'GEMINI': 'gemini',
        }
        provider_name = provider_name_map.get(provider_id)
        if not provider_name:
            return {'success': False, 'message': f'Cannot test provider: {provider_id}', 'latency_ms': None}

        # Check if API key is set
        api_key = self.get_api_key(provider_name)
        if not api_key:
            return {'success': False, 'message': 'No API key configured', 'latency_ms': None}

        try:
            start = time.time()
            llm = ProviderFactory.create_llm(
                model_id=test_model,
                provider_name=provider_name,
                temperature=0,
                streaming=False,
            )
            # Invoke with a trivial prompt
            from langchain_core.messages import HumanMessage
            llm.invoke([HumanMessage(content="Hi")])
            latency = (time.time() - start) * 1000
            return {'success': True, 'message': f'Connected', 'latency_ms': round(latency, 1)}
        except Exception as e:
            error_msg = str(e)
            # Truncate long error messages
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            return {'success': False, 'message': error_msg, 'latency_ms': None}

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
