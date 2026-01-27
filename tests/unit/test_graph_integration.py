"""Integration tests for the LangGraph conversation flow."""

from unittest.mock import AsyncMock, Mock

import pytest
from agent_config import AgentConfig, AgentPersonality, EscalationPolicy, FieldConfig, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import ConversationalAgent, LLMProvider
from agent_core.graph.builder import create_conversation_graph
from agent_runtime import ConversationStatus, StateStore


@pytest.fixture
def basic_config():
    """Create a basic agent configuration for testing."""
    return AgentConfig(
        personality=AgentPersonality(
            tone=Tone.PROFESSIONAL,
            style="concise",
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
def config_with_escalation(basic_config):
    """Create a config with escalation policies."""
    return AgentConfig(
        personality=basic_config.personality,
        llm=basic_config.llm,
        greeting=basic_config.greeting,
        fields=basic_config.fields,
        escalation_policies=[
            EscalationPolicy(
                policy_type="keyword",
                config={"keywords": ["human", "agent", "help me"]},
                reason="User requested human agent",
                enabled=True,
            )
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


class TestGraphConstruction:
    """Tests for graph construction."""

    def test_create_conversation_graph(self, basic_config, store, mock_llm_provider):
        """Test graph is created successfully."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)

        graph = create_conversation_graph(agent)

        assert graph is not None

    def test_agent_graph_property(self, basic_config, store, mock_llm_provider):
        """Test agent lazily creates graph."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)

        assert agent._graph is None

        graph = agent.graph

        assert agent._graph is not None
        assert graph is agent._graph


class TestHappyPathFlow:
    """Tests for happy path conversation flow."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, basic_config, store, mock_llm_provider):
        """Test complete conversation from start to finish."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)

        # Start conversation
        state = agent.start_conversation()

        # Provide name
        # Graph flow: check_correction (may call LLM), check_off_topic (calls LLM),
        #             extract_field (calls LLM), validate (no LLM), prompt_next (calls LLM)
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # off-topic check
                "John Doe",  # extract field
                "What's your email address?",  # prompt next
            ]
        )
        response, state = await agent.process_message(state, "My name is John Doe")
        assert "full_name" in state.get_collected_data()

        # Provide email
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # off-topic check
                "john@example.com",  # extract field
                "What's your phone number?",  # prompt next
            ]
        )
        response, state = await agent.process_message(state, "john@example.com")
        assert "email" in state.get_collected_data()

        # Provide phone
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # off-topic check
                "123-456-7890",  # extract field
                "Thank you for your information!",  # complete
            ]
        )
        response, state = await agent.process_message(state, "123-456-7890")
        assert "phone" in state.get_collected_data()
        assert state.status == ConversationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_skip_optional_field(self, basic_config, store, mock_llm_provider):
        """Test skipping optional field completes conversation."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Collect required fields
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)

        # Skip phone (optional) - provide empty/skip response
        mock_llm_provider.ainvoke = AsyncMock(side_effect=["NOT_PROVIDED", "Thank you!"])
        response, state = await agent.process_message(state, "I prefer not to share my phone")

        # Phone should not be collected but conversation continues
        assert "phone" not in state.get_collected_data()


class TestEscalationFlow:
    """Tests for escalation flow."""

    @pytest.mark.asyncio
    async def test_escalation_triggers_correctly(
        self, config_with_escalation, store, mock_llm_provider
    ):
        """Test escalation triggers on keyword match."""
        agent = ConversationalAgent(config_with_escalation, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        response, state = await agent.process_message(
            state, "I need to speak to a human agent please"
        )

        assert state.status == ConversationStatus.ESCALATED
        assert state.escalation_triggered is True
        assert "connecting" in response.lower()

    @pytest.mark.asyncio
    async def test_escalation_preserves_collected_data(
        self, config_with_escalation, store, mock_llm_provider
    ):
        """Test escalation preserves already collected data."""
        agent = ConversationalAgent(config_with_escalation, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Collect some data first
        mock_llm_provider.ainvoke = AsyncMock(side_effect=["John Doe", "What's your email?"])
        response, state = await agent.process_message(state, "My name is John Doe")

        # Then escalate
        response, state = await agent.process_message(state, "Actually, I need a human agent")

        assert state.escalation_triggered is True
        assert "full_name" in state.get_collected_data()


class TestCorrectionFlow:
    """Tests for correction handling flow."""

    @pytest.mark.asyncio
    async def test_correction_updates_field(self, basic_config, store, mock_llm_provider):
        """Test correction updates previously collected field."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Collect name
        # Graph flow: check_off_topic (LLM), extract_field (LLM), prompt_next (LLM)
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # off-topic check
                "Jon Doe",  # extract field
                "What's your email?",  # prompt next
            ]
        )
        response, state = await agent.process_message(state, "My name is Jon Doe")
        assert state.get_collected_data()["full_name"] == "Jon Doe"

        # Correct name using explicit correction pattern "No, my name is..."
        # This triggers pattern detection (no LLM call for correction check)
        # Graph flow: extract_field (LLM), prompt_next (LLM)
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "John Doe",  # Extraction
                "What's your email?",  # Next prompt
            ]
        )
        response, state = await agent.process_message(state, "No, my name is John Doe")

        # Name should be updated
        assert state.get_collected_data()["full_name"] == "John Doe"


class TestOffTopicFlow:
    """Tests for off-topic detection flow."""

    @pytest.mark.asyncio
    async def test_off_topic_redirect(self, basic_config, store, mock_llm_provider):
        """Test off-topic messages are redirected."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # Send off-topic message
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "OFF_TOPIC",  # Off-topic detection
                "I appreciate your greeting! Now, what's your full name?",
            ]
        )
        response, state = await agent.process_message(state, "Hello! How are you?")

        # Should redirect to data collection
        assert "name" in response.lower()

    @pytest.mark.asyncio
    async def test_multiple_off_topic_handled(self, basic_config, store, mock_llm_provider):
        """Test multiple off-topic messages are handled gracefully."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()

        # First off-topic
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=["OFF_TOPIC", "Let's continue - what's your name?"]
        )
        response, state = await agent.process_message(state, "What's the weather?")

        # Second off-topic
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=["OFF_TOPIC", "I understand! Could you please share your name?"]
        )
        response, state = await agent.process_message(state, "Tell me a joke")

        # Should still be asking for the same field
        assert "full_name" not in state.get_collected_data()


class TestValidationFlow:
    """Tests for validation handling flow."""

    @pytest.mark.asyncio
    async def test_invalid_email_reprompts(self, basic_config, store, mock_llm_provider):
        """Test invalid email triggers re-prompt."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()
        state.update_field_value("full_name", "John Doe", True)

        # Provide invalid email
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",  # Off-topic check
                "not-an-email",  # Extraction
                "That doesn't look like a valid email. Please provide a valid email address.",
            ]
        )
        response, state = await agent.process_message(state, "my email is not-an-email")

        # Email should not be collected
        assert "email" not in state.get_collected_data()

    @pytest.mark.asyncio
    async def test_valid_after_invalid(self, basic_config, store, mock_llm_provider):
        """Test valid input after invalid is accepted."""
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)
        state = agent.start_conversation()
        state.update_field_value("full_name", "John Doe", True)

        # First, invalid email
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",
                "invalid",
                "Please provide a valid email.",
            ]
        )
        response, state = await agent.process_message(state, "invalid")
        assert "email" not in state.get_collected_data()

        # Then, valid email
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "ON_TOPIC",
                "john@example.com",
                "What's your phone number?",
            ]
        )
        response, state = await agent.process_message(state, "john@example.com")
        assert state.get_collected_data()["email"] == "john@example.com"
