"""Tests for LLM Provider module."""

import os
from unittest.mock import Mock, patch

import pytest
from agent_config import LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_core import LLMProvider, LLMProviderError, create_llm
from langchain_openai import ChatOpenAI


class TestCreateLLM:
    """Tests for create_llm function."""

    def test_create_openai_llm_success(self):
        """Test creating OpenAI LLM with valid config."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
            temperature=0.7,
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = create_llm(config)

        assert isinstance(llm, ChatOpenAI)
        assert llm.model_name == "gpt-3.5-turbo"
        assert llm.temperature == 0.7

    def test_create_llm_missing_api_key(self):
        """Test creating LLM without API key raises error."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
            api_key_env_var="MISSING_KEY",
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                create_llm(config)

        assert "API key not found" in str(exc_info.value)
        assert "MISSING_KEY" in str(exc_info.value)

    def test_create_llm_with_max_tokens(self):
        """Test creating LLM with max_tokens specified."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-4",
            max_tokens=1000,
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = create_llm(config)

        assert isinstance(llm, ChatOpenAI)
        assert llm.max_tokens == 1000

    def test_create_llm_with_base_url(self):
        """Test creating LLM with custom base URL."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
            base_url="https://custom.api.url",
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = create_llm(config)

        assert isinstance(llm, ChatOpenAI)
        assert llm.openai_api_base == "https://custom.api.url"


class TestLLMProvider:
    """Tests for LLMProvider class."""

    def test_llm_provider_initialization(self):
        """Test LLM Provider initialization."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        assert provider.config == config
        assert provider._llm is None

    def test_llm_property_lazy_initialization(self):
        """Test LLM is created on first access."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm = provider.llm

        assert llm is not None
        assert isinstance(llm, ChatOpenAI)
        assert provider._llm is llm

    def test_llm_property_caches_instance(self):
        """Test LLM instance is cached after first access."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            llm1 = provider.llm
            llm2 = provider.llm

        assert llm1 is llm2

    def test_invoke_success(self):
        """Test successful LLM invocation."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = "Test response"

        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        # Mock the _llm directly
        provider._llm = mock_llm

        result = provider.invoke("Test prompt")

        assert result == "Test response"
        mock_llm.invoke.assert_called_once_with("Test prompt")

    def test_invoke_error_handling(self):
        """Test error handling during invocation."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API Error")

        # Mock the _llm directly
        provider._llm = mock_llm

        with pytest.raises(LLMProviderError) as exc_info:
            provider.invoke("Test prompt")

        assert "Error invoking LLM" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ainvoke_success(self):
        """Test successful async LLM invocation."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = "Async test response"

        mock_llm = Mock()

        # Create a coroutine for ainvoke
        async def mock_ainvoke(prompt):
            return mock_response

        mock_llm.ainvoke = mock_ainvoke

        # Mock the _llm directly
        provider._llm = mock_llm

        result = await provider.ainvoke("Test prompt")

        assert result == "Async test response"

    @pytest.mark.asyncio
    async def test_ainvoke_error_handling(self):
        """Test error handling during async invocation."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        )

        provider = LLMProvider(config)

        mock_llm = Mock()

        async def mock_ainvoke(prompt):
            raise Exception("Async API Error")

        mock_llm.ainvoke = mock_ainvoke

        # Mock the _llm directly
        provider._llm = mock_llm

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.ainvoke("Test prompt")

        assert "Error invoking LLM" in str(exc_info.value)
        assert "Async API Error" in str(exc_info.value)


class TestLLMConfigValidation:
    """Tests for LLMConfig validation."""

    def test_valid_llm_config(self):
        """Test creating valid LLM config."""
        config = LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=2000,
        )

        assert config.provider == LLMProviderEnum.OPENAI
        assert config.model_name == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000

    def test_temperature_validation_min(self):
        """Test temperature must be >= 0.0."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMConfig(
                provider=LLMProviderEnum.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=-0.1,
            )

    def test_temperature_validation_max(self):
        """Test temperature must be <= 2.0."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMConfig(
                provider=LLMProviderEnum.OPENAI,
                model_name="gpt-3.5-turbo",
                temperature=2.1,
            )

    def test_max_tokens_validation(self):
        """Test max_tokens must be positive."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMConfig(
                provider=LLMProviderEnum.OPENAI,
                model_name="gpt-3.5-turbo",
                max_tokens=0,
            )

    def test_empty_model_name(self):
        """Test model name cannot be empty."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMConfig(
                provider=LLMProviderEnum.OPENAI,
                model_name="",
            )

    def test_empty_api_key_env_var(self):
        """Test API key env var cannot be empty."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            LLMConfig(
                provider=LLMProviderEnum.OPENAI,
                model_name="gpt-3.5-turbo",
                api_key_env_var="",
            )

    def test_default_values(self):
        """Test LLM config default values."""
        config = LLMConfig()

        assert config.provider == LLMProviderEnum.OPENAI
        assert config.model_name == "gpt-3.5-turbo"
        assert config.temperature == 0.7
        assert config.max_tokens is None
        assert config.api_key_env_var == "OPENAI_API_KEY"
        assert config.base_url is None
