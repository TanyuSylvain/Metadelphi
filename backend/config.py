"""
Centralized configuration management for the Metadelphi application.

Configuration is stored in a TOML file (config.toml) at the project root.
If config.toml does not exist on startup, an existing .env file is migrated
into config.toml automatically.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

import tomllib
import tomli_w
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# =============================================================================
# Default model lists used only for .env migration and "add provider" templates
# =============================================================================

DEFAULT_PROVIDER_MODELS: ClassVar[Dict[str, List[Dict[str, Any]]]] = {
    "mistral": [
        {"id": "mistral-large-latest", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "mistral-medium-latest", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "mistral-small-latest", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "magistral-medium-latest", "supports_thinking": True, "thinking_locked": True, "is_image_model": False},
        {"id": "magistral-small-latest", "supports_thinking": True, "thinking_locked": True, "is_image_model": False},
    ],
    "qwen": [
        {"id": "qwen3.6-plus", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3-max-preview", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3-max", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3-235b-a22b", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3-235b-a22b-thinking-2507", "supports_thinking": True, "thinking_locked": True, "is_image_model": False},
        {"id": "qwen3-235b-a22b-instruct-2507", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3-coder-plus", "supports_thinking": False, "thinking_locked": False, "is_image_model": False},
        {"id": "qwen3.5-flash", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "deepseek-v3.2", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "glm-5", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "kimi-k2.5", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
    ],
    "glm": [
        {"id": "glm-5", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "glm-4.7", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
    ],
    "minimax": [
        {"id": "MiniMax-M2.7-highspeed", "supports_thinking": True, "thinking_locked": True, "is_image_model": False},
    ],
    "deepseek": [
        {"id": "deepseek-v4-flash", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "deepseek-v4-pro", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
    ],
    "openai": [
        {"id": "gpt-5.5", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "gpt-5.4-mini", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "gpt-image-2", "supports_thinking": False, "thinking_locked": False, "is_image_model": True},
    ],
    "gemini": [
        {"id": "gemini-3.1-pro-preview", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "gemini-3-flash-preview", "supports_thinking": True, "thinking_locked": False, "is_image_model": False},
        {"id": "gemini-3.1-flash-image-preview", "supports_thinking": False, "thinking_locked": False, "is_image_model": True},
        {"id": "gemini-2.5-flash-image", "supports_thinking": False, "thinking_locked": False, "is_image_model": True},
    ],
}


class Settings:
    """Application settings loaded from config.toml."""

    # Provider metadata for GUI configuration and internal routing.
    # Does NOT include hardcoded model lists.
    PROVIDERS: ClassVar[Dict[str, Dict[str, Any]]] = {
        "mistral": {
            "name": "Mistral AI",
            "key_env": "MISTRAL_API_KEY",
            "base_url_env": None,
            "default_base_url": None,
            "console_url": "https://console.mistral.ai/",
            "category": "llm",
            "streaming": True,
        },
        "qwen": {
            "name": "Alibaba Qwen (DashScope)",
            "key_env": "QWEN_API_KEY",
            "base_url_env": "QWEN_BASE_URL",
            "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "console_url": "https://dashscope.aliyuncs.com/",
            "category": "llm",
            "streaming": True,
        },
        "glm": {
            "name": "Zhipu GLM",
            "key_env": "GLM_API_KEY",
            "base_url_env": "GLM_BASE_URL",
            "default_base_url": "https://open.bigmodel.cn/api/paas/v4",
            "console_url": "https://open.bigmodel.cn/",
            "category": "llm",
            "streaming": True,
        },
        "minimax": {
            "name": "MiniMax",
            "key_env": "MINIMAX_API_KEY",
            "base_url_env": "MINIMAX_BASE_URL",
            "default_base_url": "https://api.minimaxi.com/v1",
            "console_url": "https://www.minimaxi.com/",
            "category": "llm",
            "streaming": True,
        },
        "deepseek": {
            "name": "DeepSeek",
            "key_env": "DEEPSEEK_API_KEY",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "default_base_url": "https://api.deepseek.com",
            "console_url": "https://platform.deepseek.com/",
            "category": "llm",
            "streaming": True,
        },
        "openai": {
            "name": "OpenAI / OpenAI-compatible",
            "key_env": "OPENAI_API_KEY",
            "base_url_env": "OPENAI_BASE_URL",
            "default_base_url": "https://api.openai.com/v1",
            "console_url": "https://platform.openai.com/api-keys",
            "category": "llm",
            "streaming": True,
        },
        "gemini": {
            "name": "Google Gemini",
            "key_env": "GEMINI_API_KEY",
            "base_url_env": "GEMINI_BASE_URL",
            "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "console_url": "https://aistudio.google.com/app/apikey",
            "category": "llm",
            "streaming": True,
        },
    }

    # Internal provider name mapping for special cases.
    _PROVIDER_NAME_TO_ID: ClassVar[Dict[str, str]] = {
        "mistral": "mistral",
        "qwen": "qwen",
        "glm": "glm",
        "minimax": "minimax",
        "deepseek": "deepseek",
        "openai": "openai",
        "gemini": "gemini",
        "gemini_image": "gemini",
        "openai_image": "openai",
    }

    _update_lock: ClassVar[threading.RLock] = threading.RLock()

    def __init__(self):
        self._config_path = Path(__file__).parent.parent / "config.toml"
        self._env_path = Path(__file__).parent.parent / ".env"

        if not self._config_path.exists() and self._env_path.exists():
            self._migrate_from_env()

        self._config = self._load_toml()
        self._ensure_defaults()

    # =========================================================================
    # Loading and persistence
    # =========================================================================

    def _load_toml(self) -> Dict[str, Any]:
        """Load configuration from config.toml."""
        if not self._config_path.exists():
            return {}
        try:
            with open(self._config_path, "rb") as f:
                return tomllib.load(f)
        except Exception as e:
            logger.error(f"Failed to load {self._config_path}: {e}")
            return {}

    def _persist(self) -> None:
        """Persist current configuration to config.toml atomically."""
        with self._update_lock:
            tmp_path = self._config_path.with_suffix(".toml.tmp")
            with open(tmp_path, "wb") as f:
                tomli_w.dump(self._strip_none_values(self._config), f)
            tmp_path.replace(self._config_path)
            logger.info(f"Persisted settings to {self._config_path}")

    def _ensure_defaults(self) -> None:
        """Ensure all required config sections exist."""
        defaults = {
            "general": {
                "api_host": "0.0.0.0",
                "api_port": 8000,
            },
            "agents": {
                "max_tool_concurrency": 5,
                "simple_max_tool_iterations": 25,
                "coworking_max_tool_iterations": 25,
            },
            "web_search": {
                "default_engine": "bailian",
                "bailian_api_key": None,
                "tavily_api_key": None,
            },
            "mcp": {
                "servers": [],
            },
            "providers": {},
        }
        changed = False
        for section, default_values in defaults.items():
            if section not in self._config or not isinstance(self._config[section], dict):
                self._config[section] = {}
                changed = True
            for key, value in default_values.items():
                if key not in self._config[section]:
                    self._config[section][key] = value
                    changed = True
        if changed:
            self._persist()

    def _migrate_from_env(self) -> None:
        """Create config.toml from an existing .env file."""
        load_dotenv(self._env_path)

        providers = {}
        for provider_id, meta in self.PROVIDERS.items():
            key_env = meta.get("key_env")
            api_key = os.environ.get(key_env) if key_env else None
            base_url_env = meta.get("base_url_env")
            base_url = os.environ.get(base_url_env) if base_url_env else meta.get("default_base_url")

            provider_cfg = {"api_key": api_key, "models": DEFAULT_PROVIDER_MODELS.get(provider_id, [])}
            if meta.get("base_url_env"):
                provider_cfg["base_url"] = base_url
            providers[provider_id] = provider_cfg

        # Legacy: Bailian/DashScope key may live under DASHSCOPE_API_KEY.
        bailian_key = os.environ.get("DASHSCOPE_API_KEY")

        config = {
            "general": {
                "api_host": os.environ.get("API_HOST", "0.0.0.0"),
                "api_port": int(os.environ.get("API_PORT", "8000")),
            },
            "agents": {
                "max_tool_concurrency": int(os.environ.get("MAX_TOOL_CONCURRENCY", "5")),
                "simple_max_tool_iterations": int(os.environ.get("SIMPLE_MAX_TOOL_ITERATIONS", "25")),
                "coworking_max_tool_iterations": int(os.environ.get("COWORKING_MAX_TOOL_ITERATIONS", "25")),
            },
            "web_search": {
                "default_engine": os.environ.get("DEFAULT_SEARCH_ENGINE", "bailian"),
                "bailian_api_key": bailian_key,
                "tavily_api_key": os.environ.get("TAVILY_API_KEY"),
            },
            "mcp": {
                "servers": [],
            },
            "providers": providers,
        }

        # Clean None values for cleaner TOML.
        config = self._strip_none_values(config)

        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._config_path, "wb") as f:
            tomli_w.dump(config, f)
        logger.info(f"Migrated settings from {self._env_path} to {self._config_path}")

    @staticmethod
    def _strip_none_values(obj: Any) -> Any:
        """Recursively remove None values from dicts and lists."""
        if isinstance(obj, dict):
            return {k: Settings._strip_none_values(v) for k, v in obj.items() if v is not None}
        if isinstance(obj, list):
            return [Settings._strip_none_values(item) for item in obj]
        return obj

    # =========================================================================
    # Config accessors
    # =========================================================================

    @property
    def api_host(self) -> str:
        return self._config["general"].get("api_host", "0.0.0.0")

    @property
    def api_port(self) -> int:
        return int(self._config["general"].get("api_port", 8000))

    @property
    def cors_origins(self) -> List[str]:
        return ["*"]

    @property
    def default_model(self) -> str:
        return "mistral"

    @property
    def model_temperature(self) -> float:
        return 0.7

    @property
    def log_level(self) -> str:
        return "INFO"

    @property
    def storage_backend(self) -> str:
        return "sqlite"

    @property
    def database_url(self) -> Optional[str]:
        return "conversations.db"

    @property
    def redis_url(self) -> Optional[str]:
        return None

    @property
    def max_tool_concurrency(self) -> int:
        return int(self._config["agents"].get("max_tool_concurrency", 5))

    @property
    def simple_max_tool_iterations(self) -> int:
        return int(self._config["agents"].get("simple_max_tool_iterations", 25))

    @property
    def coworking_max_tool_iterations(self) -> int:
        return int(self._config["agents"].get("coworking_max_tool_iterations", 25))

    @property
    def multi_agent_max_iterations(self) -> int:
        return 3

    @property
    def multi_agent_score_threshold(self) -> float:
        return 80.0

    @property
    def multi_agent_session_timeout(self) -> int:
        return 600

    @property
    def default_search_engine(self) -> str:
        return self._config["web_search"].get("default_engine", "bailian")

    @property
    def bailian_api_key(self) -> Optional[str]:
        return self._config["web_search"].get("bailian_api_key")

    @property
    def tavily_api_key(self) -> Optional[str]:
        return self._config["web_search"].get("tavily_api_key")

    # Backward-compatible alias used by legacy code.
    dashscope_api_key = bailian_api_key

    @property
    def mcp_servers(self) -> List[Dict[str, Any]]:
        return self._config.get("mcp", {}).get("servers", [])

    # Backward-compatible aliases.
    mcp_servers_config = None
    web_search_mcp_url = None
    web_parser_mcp_url = None
    mcp_transport_type = "sse"

    # Provider API keys (backward-compatible attribute names).
    @property
    def mistral_api_key(self) -> Optional[str]:
        return self._get_provider_field("mistral", "api_key")

    @property
    def qwen_api_key(self) -> Optional[str]:
        return self._get_provider_field("qwen", "api_key")

    @property
    def glm_api_key(self) -> Optional[str]:
        return self._get_provider_field("glm", "api_key")

    @property
    def zhipuai_api_key(self) -> Optional[str]:
        return self._get_provider_field("glm", "api_key")

    @property
    def minimax_api_key(self) -> Optional[str]:
        return self._get_provider_field("minimax", "api_key")

    @property
    def deepseek_api_key(self) -> Optional[str]:
        return self._get_provider_field("deepseek", "api_key")

    @property
    def openai_api_key(self) -> Optional[str]:
        return self._get_provider_field("openai", "api_key")

    @property
    def gemini_api_key(self) -> Optional[str]:
        return self._get_provider_field("gemini", "api_key")

    # Provider base URLs (backward-compatible attribute names).
    @property
    def qwen_base_url(self) -> Optional[str]:
        return self._get_provider_field("qwen", "base_url")

    @property
    def glm_base_url(self) -> Optional[str]:
        return self._get_provider_field("glm", "base_url")

    @property
    def minimax_base_url(self) -> Optional[str]:
        return self._get_provider_field("minimax", "base_url")

    @property
    def deepseek_base_url(self) -> Optional[str]:
        return self._get_provider_field("deepseek", "base_url")

    @property
    def openai_base_url(self) -> Optional[str]:
        return self._get_provider_field("openai", "base_url")

    @property
    def gemini_base_url(self) -> Optional[str]:
        return self._get_provider_field("gemini", "base_url")

    def _get_provider_field(self, provider_id: str, field: str) -> Any:
        """Get a field from a provider config."""
        provider_cfg = self._config.get("providers", {}).get(provider_id, {})
        return provider_cfg.get(field)

    # =========================================================================
    # Provider helpers
    # =========================================================================

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        provider_id = self._PROVIDER_NAME_TO_ID.get(provider, provider)
        if provider_id in {"tavily"}:
            return self.tavily_api_key
        return self._get_provider_field(provider_id, "api_key")

    def get_base_url(self, provider: str) -> Optional[str]:
        """Get base URL for a specific provider."""
        provider_id = self._PROVIDER_NAME_TO_ID.get(provider, provider)
        meta = self.PROVIDERS.get(provider_id, {})
        configured = self._get_provider_field(provider_id, "base_url")
        return configured or meta.get("default_base_url")

    def get_provider_models(self, provider_id: str) -> List[Dict[str, Any]]:
        """Return the configured models for a provider."""
        return self._get_provider_field(provider_id, "models") or []

    def find_model(self, provider_id: str, model_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific model config across all providers or a specific provider."""
        provider_id = self._PROVIDER_NAME_TO_ID.get(provider_id, provider_id)
        for model in self.get_provider_models(provider_id):
            if model.get("id") == model_id:
                return model
        return None

    def get_provider_configs(self) -> Dict[str, Dict[str, Any]]:
        """Return current provider configurations with masked keys and metadata."""
        configs = {}
        for provider_id, meta in self.PROVIDERS.items():
            provider_cfg = self._config.get("providers", {}).get(provider_id, {})
            raw_key = provider_cfg.get("api_key")
            base_url = self.get_base_url(provider_id)
            configs[provider_id] = {
                "api_key_masked": self.mask_key(raw_key),
                "api_key_set": bool(raw_key),
                "base_url": base_url,
                "has_base_url": meta.get("base_url_env") is not None,
                "display_name": meta["name"],
                "console_url": meta["console_url"],
                "default_base_url": meta.get("default_base_url"),
                "category": meta.get("category", "llm"),
                "models": self.get_provider_models(provider_id),
            }
        return configs

    def get_search_engine_status(self) -> Dict[str, Any]:
        """Return configured search engines and the current default."""
        bailian_available = bool(self.bailian_api_key)
        tavily_available = bool(self.tavily_api_key)
        default = self.default_search_engine.lower()
        if default not in {"bailian", "tavily"}:
            default = "bailian"
        return {
            "default": default,
            "available": {
                "bailian": bailian_available,
                "tavily": tavily_available,
            },
            "configured": bailian_available or tavily_available,
        }

    def get_mcp_servers(self) -> List[Dict[str, Any]]:
        """Get configured MCP servers with resolved API keys."""
        servers = []
        for server in self.mcp_servers:
            api_key_env = server.get("api_key_env")
            api_key = os.environ.get(api_key_env) if api_key_env else None
            servers.append({
                "name": server.get("name", "unnamed"),
                "url": server.get("url", ""),
                "transport": server.get("transport", "sse"),
                "api_key": api_key,
                "headers": server.get("headers", {}),
            })
        return servers

    @staticmethod
    def mask_key(key: Optional[str]) -> Optional[str]:
        """Mask an API key, showing only the last 4 characters."""
        if not key or len(key) < 8:
            return None
        return "********" + key[-4:]

    # =========================================================================
    # Updates and validation
    # =========================================================================

    def get_full_config(self) -> Dict[str, Any]:
        """Return the full current configuration."""
        return self._config

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Validate and replace the full application configuration.

        Raises:
            ValueError: with a descriptive message listing invalid/missing fields.
        """
        errors = self._validate_config(new_config)
        if errors:
            raise ValueError("; ".join(errors))

        with self._update_lock:
            self._config = new_config
            self._ensure_defaults()
            self._persist()

    def _validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate a candidate configuration and return a list of error messages."""
        errors = []

        if not isinstance(config, dict):
            return ["Configuration must be an object"]

        # General
        general = config.get("general", {})
        if not isinstance(general, dict):
            errors.append("general must be an object")
        else:
            if not isinstance(general.get("api_port", 8000), int):
                errors.append("general.api_port must be an integer")

        # Agents
        agents = config.get("agents", {})
        if not isinstance(agents, dict):
            errors.append("agents must be an object")
        else:
            for key in ("max_tool_concurrency", "simple_max_tool_iterations", "coworking_max_tool_iterations"):
                try:
                    value = agents.get(key)
                    if value is not None and int(value) < 1:
                        errors.append(f"agents.{key} must be a positive integer")
                except (TypeError, ValueError):
                    errors.append(f"agents.{key} must be a positive integer")

        # Web search
        web_search = config.get("web_search", {})
        if not isinstance(web_search, dict):
            errors.append("web_search must be an object")
        elif web_search.get("default_engine") not in {None, "bailian", "tavily"}:
            errors.append("web_search.default_engine must be 'bailian' or 'tavily'")

        # MCP
        mcp = config.get("mcp", {})
        if not isinstance(mcp, dict):
            errors.append("mcp must be an object")
        else:
            servers = mcp.get("servers", [])
            if not isinstance(servers, list):
                errors.append("mcp.servers must be a list")
            else:
                for i, server in enumerate(servers):
                    if not isinstance(server, dict):
                        errors.append(f"mcp.servers[{i}] must be an object")
                        continue
                    if not server.get("name"):
                        errors.append(f"mcp.servers[{i}].name is required")
                    if not server.get("url"):
                        errors.append(f"mcp.servers[{i}].url is required")

        # Providers
        providers = config.get("providers", {})
        if not isinstance(providers, dict):
            errors.append("providers must be an object")
        else:
            for provider_id, provider_cfg in providers.items():
                if provider_id not in self.PROVIDERS:
                    errors.append(f"providers.{provider_id} is not a supported provider")
                    continue
                if not isinstance(provider_cfg, dict):
                    errors.append(f"providers.{provider_id} must be an object")
                    continue

                meta = self.PROVIDERS[provider_id]
                models = provider_cfg.get("models", [])
                if not isinstance(models, list):
                    errors.append(f"providers.{provider_id}.models must be a list")
                    continue
                if len(models) == 0:
                    errors.append(f"providers.{provider_id}.models must contain at least one model")

                model_ids = set()
                for i, model in enumerate(models):
                    prefix = f"providers.{provider_id}.models[{i}]"
                    if not isinstance(model, dict):
                        errors.append(f"{prefix} must be an object")
                        continue
                    model_id = model.get("id")
                    if not model_id or not str(model_id).strip():
                        errors.append(f"{prefix}.id is required")
                    elif model_id in model_ids:
                        errors.append(f"{prefix}.id '{model_id}' is duplicated")
                    else:
                        model_ids.add(model_id)

                    for bool_field in ("supports_thinking", "thinking_locked", "is_image_model"):
                        value = model.get(bool_field)
                        if value is not None and not isinstance(value, bool):
                            errors.append(f"{prefix}.{bool_field} must be a boolean")

                if meta.get("base_url_env") and not provider_cfg.get("base_url"):
                    errors.append(f"providers.{provider_id}.base_url is required")

        return errors

    def update_default_search_engine(self, engine: str) -> bool:
        """Update the default search engine and persist to config.toml."""
        engine = engine.lower()
        if engine not in {"bailian", "tavily"}:
            return False
        with self._update_lock:
            self._config.setdefault("web_search", {})["default_engine"] = engine
            self._persist()
        return True

    def test_provider_model(self, provider_id: str, model_id: str) -> Dict[str, Any]:
        """Test a saved provider/model connection using a ping-pong prompt."""
        provider_id = provider_id.lower()
        if provider_id not in self.PROVIDERS:
            return {"success": False, "message": f"Unknown provider: {provider_id}", "latency_ms": None}

        model = self.find_model(provider_id, model_id)
        if not model:
            return {"success": False, "message": f"Model '{model_id}' not configured for {provider_id}", "latency_ms": None}

        api_key = self.get_api_key(provider_id)
        base_url = self.get_base_url(provider_id)
        if not api_key:
            return {"success": False, "message": "No API key configured", "latency_ms": None}

        return self.test_model(provider_id, model_id, api_key, base_url, model.get("is_image_model", False))

    def test_model(
        self,
        provider_id: str,
        model_id: str,
        api_key: str,
        base_url: Optional[str] = None,
        is_image_model: bool = False,
    ) -> Dict[str, Any]:
        """Test a provider/model with explicit credentials (supports unsaved config)."""
        from backend.providers.registry import ProviderRegistry

        provider_id = provider_id.lower()
        if provider_id not in self.PROVIDERS:
            return {"success": False, "message": f"Unknown provider: {provider_id}", "latency_ms": None}

        if not api_key:
            return {"success": False, "message": "No API key provided", "latency_ms": None}

        try:
            provider_class = ProviderRegistry._providers[provider_id]
            if is_image_model and provider_id in ProviderRegistry._image_providers:
                provider_class = ProviderRegistry._image_providers[provider_id]
            provider = provider_class()
            # Bypass the saved-config model validation so the test uses the
            # unsupplied model ID and credentials currently in the form.
            provider.validate_model_id = lambda m: m

            kwargs = {}
            if base_url:
                kwargs["base_url"] = base_url

            start = time.time()
            if is_image_model:
                # For image models, just verify initialization succeeds.
                provider.initialize(model_id=model_id, api_key=api_key, **kwargs)
                return {"success": True, "message": "Configured", "latency_ms": None}

            llm = provider.initialize(model_id=model_id, api_key=api_key, temperature=0, streaming=False, **kwargs)
            from langchain_core.messages import HumanMessage
            llm.invoke([HumanMessage(content="Hi")])
            latency = (time.time() - start) * 1000
            return {"success": True, "message": "Success", "latency_ms": round(latency, 1)}
        except Exception as e:
            error_msg = str(e)
            if len(error_msg) > 300:
                error_msg = error_msg[:300] + "..."
            return {"success": False, "message": error_msg, "latency_ms": None}


# Global settings instance
settings = Settings()
