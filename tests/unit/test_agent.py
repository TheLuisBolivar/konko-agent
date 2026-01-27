"""Tests for ConversationalAgent module."""

from unittest.mock import AsyncMock, Mock

import pytest
from agent_config import AgentConfig, AgentPersonality, FieldConfig, Formality, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import AgentError, ConversationalAgent, LLMProvider
from agent_runtime import ConversationState, MessageRole, StateStore


@pytest.fixture
def basic_config():
    """Create a basic agent configuration for testing."""
    return AgentConfig(
        personality=AgentPersonality(
            tone=Tone.PROFESSIONAL,
            style="concise",
            formality=Formality.NEUTRAL,
            emoji_usage=False,
        ),
        llm=LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
            temperature=0.7,
        ),
        greeting="Hello! I'm here to help collect some information.",
        fields=[
            FieldConfig(name="full_name", field_type="text", required=True),
            FieldConfig(name="email", field_type="email", required=True),
            FieldConfig(name="phone", field_type="phone", required=False),
        ],
    )


@pytest.fixture
def store():
    """Create an in-memory state store for testing."""
    return StateStore()


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock(spec=LLMProvider)
    provider.invoke = Mock(return_value="Test response")
    provider.ainvoke = AsyncMock(return_value="Test response")
    return provider


class TestConversationalAgentInit:
    """Tests for agent initialization."""

    def test_agent_initialization(self, basic_config, store):
        """Test basic agent initialization."""
        agent = ConversationalAgent(basic_config, store)

        assert agent.config == basic_config
        assert agent.store == store
        assert agent._llm_provider is None

    def test_agent_with_custom_llm_provider(self, basic_config, store, mock_llm_provider):
        """Test agent initialization with custom LLM provider."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)

        assert agent._llm_provider == mock_llm_provider
        assert agent.llm_provider == mock_llm_provider


class TestStartConversation:
    """Tests for starting conversations."""

    def test_start_conversation_creates_state(self, basic_config, store):
        """Test that starting a conversation creates a new state."""
        agent = ConversationalAgent(basic_config, store)

        state = agent.start_conversation()

        assert state is not None
        assert len(state.messages) == 1
        assert state.messages[0].role == MessageRole.AGENT
        assert state.messages[0].content == basic_config.greeting

    def test_start_conversation_stores_state(self, basic_config, store):
        """Test that started conversation is stored."""
        agent = ConversationalAgent(basic_config, store)

        state = agent.start_conversation()

        # Verify state is in store
        retrieved = store.get(state.session_id)
        assert retrieved is not None
        assert retrieved.session_id == state.session_id


class TestGetNextFieldToCollect:
    """Tests for field collection logic."""

    def test_get_next_field_returns_first_required(self, basic_config, store):
        """Test getting first required field."""
        agent = ConversationalAgent(basic_config, store)
        state = ConversationState()

        next_field = agent.get_next_field_to_collect(state)

        assert next_field is not None
        assert next_field.name == "full_name"
        assert next_field.required is True

    def test_get_next_field_skips_collected(self, basic_config, store):
        """Test that collected fields are skipped."""
        agent = ConversationalAgent(basic_config, store)
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)

        next_field = agent.get_next_field_to_collect(state)

        assert next_field is not None
        assert next_field.name == "email"

    def test_get_next_field_returns_optional_after_required(self, basic_config, store):
        """Test optional fields are returned after required."""
        agent = ConversationalAgent(basic_config, store)
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)

        next_field = agent.get_next_field_to_collect(state)

        assert next_field is not None
        assert next_field.name == "phone"
        assert next_field.required is False

    def test_get_next_field_returns_none_when_all_collected(self, basic_config, store):
        """Test None is returned when all fields are collected."""
        agent = ConversationalAgent(basic_config, store)
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)

        next_field = agent.get_next_field_to_collect(state)

        assert next_field is None


class TestFieldValidation:
    """Tests for field value validation."""

    def test_validate_email_valid(self, basic_config, store):
        """Test valid email validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="email", field_type="email", required=True)

        assert agent._validate_field_value(field, "test@example.com") is True
        assert agent._validate_field_value(field, "user.name+tag@domain.co.uk") is True

    def test_validate_email_invalid(self, basic_config, store):
        """Test invalid email validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="email", field_type="email", required=True)

        assert agent._validate_field_value(field, "invalid-email") is False
        assert agent._validate_field_value(field, "missing@domain") is False
        assert agent._validate_field_value(field, "@nodomain.com") is False

    def test_validate_phone_valid(self, basic_config, store):
        """Test valid phone validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="phone", field_type="phone", required=True)

        assert agent._validate_field_value(field, "123-456-7890") is True
        assert agent._validate_field_value(field, "(555) 123-4567") is True
        assert agent._validate_field_value(field, "+1 555 123 4567") is True

    def test_validate_phone_invalid(self, basic_config, store):
        """Test invalid phone validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="phone", field_type="phone", required=True)

        assert agent._validate_field_value(field, "abc") is False
        assert agent._validate_field_value(field, "123") is False  # Too short

    def test_validate_url_valid(self, basic_config, store):
        """Test valid URL validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="website", field_type="url", required=True)

        assert agent._validate_field_value(field, "https://example.com") is True
        assert agent._validate_field_value(field, "http://test.org/path") is True

    def test_validate_url_invalid(self, basic_config, store):
        """Test invalid URL validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="website", field_type="url", required=True)

        assert agent._validate_field_value(field, "example.com") is False
        assert agent._validate_field_value(field, "ftp://invalid") is False

    def test_validate_number_valid(self, basic_config, store):
        """Test valid number validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="age", field_type="number", required=True)

        assert agent._validate_field_value(field, "25") is True
        assert agent._validate_field_value(field, "3.14") is True
        assert agent._validate_field_value(field, "-10") is True

    def test_validate_number_invalid(self, basic_config, store):
        """Test invalid number validation."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="age", field_type="number", required=True)

        assert agent._validate_field_value(field, "abc") is False
        assert agent._validate_field_value(field, "12abc") is False

    def test_validate_text_always_valid(self, basic_config, store):
        """Test text type is always valid."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="name", field_type="text", required=True)

        assert agent._validate_field_value(field, "John Doe") is True
        assert agent._validate_field_value(field, "Any text here!") is True

    def test_validate_special_values(self, basic_config, store):
        """Test special extraction values are invalid."""
        agent = ConversationalAgent(basic_config, store)
        field = FieldConfig(name="name", field_type="text", required=True)

        assert agent._validate_field_value(field, "NOT_PROVIDED") is False
        assert agent._validate_field_value(field, "INVALID") is False
        assert agent._validate_field_value(field, "") is False


class TestBuildPrompts:
    """Tests for prompt building."""

    def test_build_system_prompt_professional(self, basic_config, store):
        """Test system prompt for professional tone."""
        agent = ConversationalAgent(basic_config, store)

        prompt = agent._build_system_prompt()

        assert "professional" in prompt.lower()
        assert "concise" in prompt.lower()
        assert "neutral" in prompt.lower()
        assert "Do not use emojis" in prompt

    def test_build_system_prompt_with_emojis(self, store):
        """Test system prompt with emoji usage enabled."""
        config = AgentConfig(
            personality=AgentPersonality(
                tone=Tone.FRIENDLY,
                style="warm",
                emoji_usage=True,
                emoji_list=["😊", "👋", "✅"],
            ),
            greeting="Hi!",
            fields=[FieldConfig(name="name", field_type="text", required=True)],
        )
        agent = ConversationalAgent(config, store)

        prompt = agent._build_system_prompt()

        assert "friendly" in prompt.lower()
        assert "You may use emojis" in prompt

    def test_build_field_prompt_includes_context(self, basic_config, store):
        """Test field prompt includes conversation context."""
        agent = ConversationalAgent(basic_config, store)
        state = ConversationState()
        state.add_message(MessageRole.AGENT, "Hello!")
        state.add_message(MessageRole.USER, "Hi there")
        field = FieldConfig(
            name="full_name", field_type="text", required=True, prompt_hint="What's your name?"
        )

        prompt = agent._build_field_prompt(field, state)

        assert "full_name" in prompt
        assert "text" in prompt
        assert "What's your name?" in prompt
        assert "Hello!" in prompt
        assert "Hi there" in prompt


class TestProcessMessage:
    """Tests for message processing."""

    @pytest.mark.asyncio
    async def test_process_message_adds_user_message(self, basic_config, store, mock_llm_provider):
        """Test that user message is added to state."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        mock_llm_provider.ainvoke = AsyncMock(side_effect=["John Doe", "What's your email?"])

        response, updated_state = await agent.process_message(state, "My name is John Doe")

        # Find user messages
        user_messages = [m for m in updated_state.messages if m.role == MessageRole.USER]
        assert len(user_messages) == 1
        assert user_messages[0].content == "My name is John Doe"

    @pytest.mark.asyncio
    async def test_process_message_extracts_field_value(
        self, basic_config, store, mock_llm_provider
    ):
        """Test that field values are extracted from messages."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Graph flow: check_off_topic (LLM), extract_field (LLM), prompt_next (LLM)
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # off-topic check
                "John Doe",  # extract field
                "Great! What's your email address?",  # prompt next
            ]
        )

        response, updated_state = await agent.process_message(state, "My name is John Doe")

        collected = updated_state.get_collected_data()
        assert "full_name" in collected
        assert collected["full_name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_process_message_completes_when_all_collected(
        self, basic_config, store, mock_llm_provider
    ):
        """Test conversation completes when all fields are collected."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Pre-fill required fields
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)

        mock_llm_provider.ainvoke = AsyncMock(return_value="Thank you for providing your info!")

        response, updated_state = await agent.process_message(state, "That's all")

        assert updated_state.status.value == "completed"

    @pytest.mark.asyncio
    async def test_process_message_handles_invalid_extraction(
        self, basic_config, store, mock_llm_provider
    ):
        """Test handling of invalid field extraction."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Mock: extraction returns invalid, then asks again
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=["NOT_PROVIDED", "Could you please tell me your name?"]
        )

        response, updated_state = await agent.process_message(state, "Hello!")

        # Field should not be collected
        collected = updated_state.get_collected_data()
        assert "full_name" not in collected


class TestAgentError:
    """Tests for AgentError."""

    def test_agent_error_message(self):
        """Test AgentError can be raised with message."""
        error = AgentError("Test error message")
        assert str(error) == "Test error message"

    def test_agent_error_inheritance(self):
        """Test AgentError inherits from Exception."""
        error = AgentError("Test")
        assert isinstance(error, Exception)
