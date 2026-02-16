"""
Centralized configuration management for the LLM GUI application.
"""

import os
from typing import Dict, Optional, List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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
    minimax_base_url: str = "https://api.minimax.io/v1"
    deepseek_base_url: str = "https://api.deepseek.com"
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"

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
            "gemini": self.gemini_api_key
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
            "gemini": self.gemini_base_url
        }
        return url_map.get(provider)


# Global settings instance
settings = Settings()
