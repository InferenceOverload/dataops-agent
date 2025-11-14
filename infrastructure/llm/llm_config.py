"""
LLM Configuration Management

Centralized configuration for LLM providers across workflows.

Configuration Priority (highest to lowest):
1. Environment variables (.env file)
2. Workflow-specific config (passed at runtime)
3. Default values (defined here)

Supported Providers:
- anthropic: Direct Anthropic API (requires ANTHROPIC_API_KEY)
- bedrock: AWS Bedrock Anthropic models (uses AWS credentials)

Usage:
    from infrastructure.llm.llm_config import LLMConfig, get_llm_config

    config = get_llm_config()
    provider = config.get_provider()
    model = config.get_model()
"""

import os
from typing import Optional, Dict, Any, Literal
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class AnthropicConfig(BaseModel):
    """Anthropic API Configuration"""
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None
    temperature: float = 0.7


class BedrockConfig(BaseModel):
    """AWS Bedrock Configuration"""
    model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    region: str = "us-east-1"
    temperature: float = 0.7


LLMProvider = Literal["anthropic", "bedrock"]


class LLMConfig:
    """
    Central LLM configuration manager.

    Reads configuration from:
    1. Environment variables (highest priority)
    2. Runtime overrides
    3. Default values (lowest priority)

    Environment Variables:
    - LLM_PROVIDER: Provider to use ('anthropic' or 'bedrock')
    - ANTHROPIC_API_KEY: API key for direct Anthropic access
    - ANTHROPIC_MODEL: Model name for Anthropic API
    - BEDROCK_MODEL_ID: Model ID for AWS Bedrock
    - BEDROCK_REGION: AWS region for Bedrock (falls back to AWS_REGION)
    - LLM_TEMPERATURE: Temperature setting for all providers
    """

    def __init__(self, overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM configuration.

        Args:
            overrides: Runtime configuration overrides
        """
        self.overrides = overrides or {}

        # Load provider preference
        self.provider = self._get_provider()

        # Load Anthropic config
        self.anthropic_config = AnthropicConfig(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )

        # Load Bedrock config
        self.bedrock_config = BedrockConfig(
            model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0"),
            region=os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )

    def _get_provider(self) -> LLMProvider:
        """
        Determine which LLM provider to use.

        Returns:
            Provider name ('anthropic' or 'bedrock')
        """
        # Check overrides first
        if "provider" in self.overrides:
            provider = self.overrides["provider"]
            if provider in ["anthropic", "bedrock"]:
                return provider

        # Check environment variable
        env_provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
        if env_provider in ["anthropic", "bedrock"]:
            return env_provider

        # Default to anthropic
        return "anthropic"

    def get_provider(self) -> LLMProvider:
        """
        Get the configured LLM provider.

        Returns:
            Provider name ('anthropic' or 'bedrock')
        """
        return self.provider

    def get_model(self) -> str:
        """
        Get the model name/ID for the current provider.

        Returns:
            Model name (Anthropic) or Model ID (Bedrock)
        """
        if "model" in self.overrides:
            return self.overrides["model"]

        if self.provider == "bedrock":
            return self.bedrock_config.model_id
        else:
            return self.anthropic_config.model

    def get_temperature(self) -> float:
        """
        Get the temperature setting.

        Returns:
            Temperature value (0.0 to 1.0)
        """
        if "temperature" in self.overrides:
            return self.overrides["temperature"]

        return self.anthropic_config.temperature

    def get_anthropic_api_key(self) -> Optional[str]:
        """
        Get Anthropic API key.

        Returns:
            API key or None if not configured

        Raises:
            ValueError: If provider is 'anthropic' but no API key is configured
        """
        if "anthropic_api_key" in self.overrides:
            return self.overrides["anthropic_api_key"]

        api_key = self.anthropic_config.api_key

        if self.provider == "anthropic" and not api_key:
            raise ValueError(
                "Anthropic API key not configured. Set ANTHROPIC_API_KEY environment variable "
                "or pass anthropic_api_key in overrides."
            )

        return api_key

    def get_bedrock_region(self) -> str:
        """
        Get AWS region for Bedrock.

        Returns:
            AWS region string
        """
        if "bedrock_region" in self.overrides:
            return self.overrides["bedrock_region"]

        return self.bedrock_config.region

    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get configuration as a dictionary for logging/debugging.

        Returns:
            Dict with current configuration (sensitive data masked)
        """
        config = {
            "provider": self.provider,
            "model": self.get_model(),
            "temperature": self.get_temperature(),
        }

        if self.provider == "anthropic":
            config["api_key_configured"] = bool(self.anthropic_config.api_key)
        else:
            config["bedrock_region"] = self.get_bedrock_region()

        return config


# Global config instance
_global_config = None


def get_llm_config(overrides: Optional[Dict[str, Any]] = None) -> LLMConfig:
    """
    Get global LLM configuration instance.

    Args:
        overrides: Runtime configuration overrides

    Returns:
        LLMConfig instance
    """
    global _global_config

    if _global_config is None or overrides:
        _global_config = LLMConfig(overrides)

    return _global_config
