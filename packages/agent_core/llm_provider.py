"""LLM Provider for AI Agent.

This module provides LLM initialization and interface for making calls to
different LLM providers (OpenAI, Anthropic).
"""

import os
from typing import Optional, cast

from agent_config import LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from langchain_core.language_models import BaseChatModel  # type: ignore[import-not-found]
from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]


class LLMProviderError(Exception):
    """Raised when there's an error with the LLM provider."""

    pass


def create_llm(config: LLMConfig) -> BaseChatModel:
    """Create and configure an LLM instance based on configuration.

    Args:
        config: LLM configuration

    Returns:
        Initialized LLM instance

    Raises:
        LLMProviderError: If provider is not supported or configuration is invalid
        ValueError: If API key is not found in environment variables
    """
    # Get API key from environment
    api_key = os.getenv(config.api_key_env_var)
    if not api_key:
        raise ValueError(
            f"API key not found in environment variable '{config.api_key_env_var}'. "
            f"Please set it before using the LLM provider."
        )

    # Common parameters
    common_params = {
        "model": config.model_name,
        "temperature": config.temperature,
        "api_key": api_key,
    }

    if config.max_tokens is not None:
        common_params["max_tokens"] = config.max_tokens

    # Provider-specific initialization
    if config.provider in (LLMProviderEnum.OPENAI, LLMProviderEnum.ANTHROPIC):
        # Both OpenAI and Anthropic use OpenAI-compatible API
        # In production, Anthropic would use langchain-anthropic
        if config.base_url:
            common_params["base_url"] = config.base_url
        return ChatOpenAI(**common_params)

    raise LLMProviderError(f"Unsupported LLM provider: {config.provider}")


class LLMProvider:
    """LLM Provider wrapper with error handling and convenience methods."""

    def __init__(self, config: LLMConfig):
        """Initialize LLM Provider.

        Args:
            config: LLM configuration
        """
        self.config = config
        self._llm: Optional[BaseChatModel] = None

    @property
    def llm(self) -> BaseChatModel:
        """Get or create LLM instance.

        Returns:
            Initialized LLM instance
        """
        if self._llm is None:
            self._llm = create_llm(self.config)
        return self._llm

    def invoke(self, prompt: str) -> str:
        """Invoke LLM with a prompt and return the response.

        Args:
            prompt: Input prompt for the LLM

        Returns:
            LLM response as string

        Raises:
            LLMProviderError: If there's an error during invocation
        """
        try:
            response = self.llm.invoke(prompt)
            return cast(str, response.content)
        except Exception as e:
            raise LLMProviderError(f"Error invoking LLM: {str(e)}") from e

    async def ainvoke(self, prompt: str) -> str:
        """Async invoke LLM with a prompt and return the response.

        Args:
            prompt: Input prompt for the LLM

        Returns:
            LLM response as string

        Raises:
            LLMProviderError: If there's an error during invocation
        """
        try:
            response = await self.llm.ainvoke(prompt)
            return cast(str, response.content)
        except Exception as e:
            raise LLMProviderError(f"Error invoking LLM: {str(e)}") from e
