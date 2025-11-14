"""
LLM Factory

Factory for creating LLM instances based on configuration.

Provides a unified interface for creating LLM clients that work with LangGraph,
abstracting away the differences between Anthropic API and AWS Bedrock.

Usage:
    from infrastructure.llm.llm_factory import create_llm

    # Uses configuration from environment variables
    llm = create_llm()

    # Override configuration at runtime
    llm = create_llm(provider="bedrock", temperature=0.5)
"""

from typing import Optional, Dict, Any, Union
from langchain_anthropic import ChatAnthropic
from langchain_aws import ChatBedrock
from infrastructure.llm.llm_config import get_llm_config, LLMConfig


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> Union[ChatAnthropic, ChatBedrock]:
    """
    Create an LLM client based on configuration.

    This factory creates LLM clients that are compatible with LangGraph.
    Both ChatAnthropic and ChatBedrock implement the same Langchain interface,
    so they can be used interchangeably in workflows.

    Args:
        provider: Override provider ('anthropic' or 'bedrock')
        model: Override model name/ID
        temperature: Override temperature setting
        **kwargs: Additional provider-specific arguments

    Returns:
        LLM client instance (ChatAnthropic or ChatBedrock)

    Raises:
        ValueError: If configuration is invalid or required credentials are missing

    Examples:
        # Use environment configuration
        llm = create_llm()

        # Override provider
        llm = create_llm(provider="bedrock")

        # Override model and temperature
        llm = create_llm(model="claude-sonnet-4-20250514", temperature=0.5)

        # Use Bedrock with custom region
        llm = create_llm(provider="bedrock", region_name="us-west-2")
    """
    # Build overrides dict
    overrides = {}
    if provider:
        overrides["provider"] = provider
    if model:
        overrides["model"] = model
    if temperature is not None:
        overrides["temperature"] = temperature

    # Get configuration
    config = get_llm_config(overrides if overrides else None)

    # Create appropriate LLM client
    if config.get_provider() == "bedrock":
        return _create_bedrock_llm(config, **kwargs)
    else:
        return _create_anthropic_llm(config, **kwargs)


def _create_anthropic_llm(config: LLMConfig, **kwargs) -> ChatAnthropic:
    """
    Create ChatAnthropic instance.

    Args:
        config: LLM configuration
        **kwargs: Additional arguments for ChatAnthropic

    Returns:
        ChatAnthropic instance
    """
    # Build parameters
    params = {
        "model": config.get_model(),
        "api_key": config.get_anthropic_api_key(),
        "temperature": config.get_temperature(),
    }

    # Add any additional kwargs
    params.update(kwargs)

    return ChatAnthropic(**params)


def _create_bedrock_llm(config: LLMConfig, **kwargs) -> ChatBedrock:
    """
    Create ChatBedrock instance.

    Args:
        config: LLM configuration
        **kwargs: Additional arguments for ChatBedrock

    Returns:
        ChatBedrock instance
    """
    # Build parameters
    params = {
        "model_id": config.get_model(),
        "region_name": config.get_bedrock_region(),
        "model_kwargs": {
            "temperature": config.get_temperature(),
        },
    }

    # Add any additional kwargs (can override model_kwargs)
    if "model_kwargs" in kwargs:
        params["model_kwargs"].update(kwargs.pop("model_kwargs"))

    params.update(kwargs)

    return ChatBedrock(**params)


# Convenience function for getting configured provider info
def get_llm_info() -> Dict[str, Any]:
    """
    Get information about the currently configured LLM provider.

    Useful for debugging and logging.

    Returns:
        Dict with provider configuration details
    """
    config = get_llm_config()
    return config.get_config_dict()
