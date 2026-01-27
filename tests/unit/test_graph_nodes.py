"""Tests for graph node functions."""

from unittest.mock import AsyncMock, Mock

import pytest
from agent_config import AgentConfig, AgentPersonality, FieldConfig, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import ConversationalAgent, LLMProvider
from agent_core.graph.nodes import (
    check_correction_node,
    check_escalation_node,
    check_off_topic_node,
    complete_node,
    escalate_node,
    extract_field_node,
    prompt_next_node,
    validate_node,
)
from agent_core.graph.state import create_initial_state
from agent_runtime import ConversationState, StateStore


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


@pytest.fixture
def agent(basic_config, store, mock_llm_provider):
    """Create an agent for testing."""
    return ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)


class TestCheckEscalationNode:
    """Tests for check_escalation_node."""

    @pytest.mark.asyncio
    async def test_no_escalation_when_no_policies(self, agent):
        """Test no escalation when no policies configured."""
        state = ConversationState()
        graph_state = create_initial_state(state, "Hello")

        result = await check_escalation_node(graph_state, agent)

        assert result["should_escalate"] is False
        assert result["escalation_reason"] is None

    @pytest.mark.asyncio
    async def test_escalation_detected(self, basic_config, store, mock_llm_provider):
        """Test escalation is detected when policy triggers."""
        from agent_config import EscalationPolicy

        config_with_escalation = AgentConfig(
            personality=basic_config.personality,
            llm=basic_config.llm,
            greeting=basic_config.greeting,
            fields=basic_config.fields,
            escalation_policies=[
                EscalationPolicy(
                    policy_type="keyword",
                    config={"keywords": ["help", "agent"]},
                    reason="User requested human agent",
                    enabled=True,
                )
            ],
        )

        agent = ConversationalAgent(config_with_escalation, store, llm_provider=mock_llm_provider)
        state = ConversationState()
        graph_state = create_initial_state(state, "I need to speak to a human agent")

        result = await check_escalation_node(graph_state, agent)

        assert result["should_escalate"] is True
        assert result["escalation_reason"] is not None


class TestCheckCorrectionNode:
    """Tests for check_correction_node."""

    @pytest.mark.asyncio
    async def test_no_correction_for_normal_message(self, agent):
        """Test no correction detected for normal messages."""
        state = ConversationState()
        graph_state = create_initial_state(state, "My name is John")

        result = await check_correction_node(graph_state, agent)

        assert result["is_correction"] is False
        assert result["correction_field"] is None

    @pytest.mark.asyncio
    async def test_correction_detected_with_pattern(self, agent, mock_llm_provider):
        """Test correction detected with pattern match."""
        state = ConversationState()
        state.update_field_value("email", "wrong@example.com", True)
        graph_state = create_initial_state(state, "No, my email is correct@example.com")

        result = await check_correction_node(graph_state, agent)

        assert result["is_correction"] is True

    @pytest.mark.asyncio
    async def test_correction_with_actually_keyword(self, agent, mock_llm_provider):
        """Test correction detected with 'actually' keyword."""
        state = ConversationState()
        state.update_field_value("full_name", "Jon Doe", True)
        graph_state = create_initial_state(state, "Actually, it should be John Doe")

        # Mock LLM response for correction detection
        mock_llm_provider.ainvoke = AsyncMock(return_value="CORRECTION:UNKNOWN")

        result = await check_correction_node(graph_state, agent)

        assert result["is_correction"] is True


class TestCheckOffTopicNode:
    """Tests for check_off_topic_node."""

    @pytest.mark.asyncio
    async def test_off_topic_greeting(self, agent):
        """Test off-topic detected for greetings."""
        state = ConversationState()
        graph_state = create_initial_state(state, "Hello!")

        result = await check_off_topic_node(graph_state, agent)

        assert result["is_off_topic"] is True

    @pytest.mark.asyncio
    async def test_on_topic_email_response(self, agent, mock_llm_provider):
        """Test on-topic for relevant response."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        graph_state = create_initial_state(state, "john@example.com")

        # Mock LLM response for off-topic check
        mock_llm_provider.ainvoke = AsyncMock(return_value="ON_TOPIC")

        result = await check_off_topic_node(graph_state, agent)

        assert result["is_off_topic"] is False

    @pytest.mark.asyncio
    async def test_off_topic_question(self, agent, mock_llm_provider):
        """Test off-topic for unrelated questions."""
        state = ConversationState()
        graph_state = create_initial_state(state, "What's the weather like today?")

        # Mock LLM response for off-topic check
        mock_llm_provider.ainvoke = AsyncMock(return_value="OFF_TOPIC")

        result = await check_off_topic_node(graph_state, agent)

        assert result["is_off_topic"] is True


class TestExtractFieldNode:
    """Tests for extract_field_node."""

    @pytest.mark.asyncio
    async def test_extract_name_value(self, agent, mock_llm_provider):
        """Test extracting name field value."""
        state = ConversationState()
        graph_state = create_initial_state(state, "My name is John Doe")

        mock_llm_provider.ainvoke = AsyncMock(return_value="John Doe")

        result = await extract_field_node(graph_state, agent)

        assert result["extracted_value"] == "John Doe"
        assert result["current_field"] == "full_name"

    @pytest.mark.asyncio
    async def test_extract_not_provided(self, agent, mock_llm_provider):
        """Test extraction returns None for NOT_PROVIDED."""
        state = ConversationState()
        graph_state = create_initial_state(state, "I don't know")

        mock_llm_provider.ainvoke = AsyncMock(return_value="NOT_PROVIDED")

        result = await extract_field_node(graph_state, agent)

        assert result["extracted_value"] is None

    @pytest.mark.asyncio
    async def test_extract_correction_field(self, agent, mock_llm_provider):
        """Test extraction for correction targets the correct field."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        graph_state = create_initial_state(state, "No, my email is john@test.com")
        graph_state["is_correction"] = True
        graph_state["correction_field"] = "email"

        mock_llm_provider.ainvoke = AsyncMock(return_value="john@test.com")

        result = await extract_field_node(graph_state, agent)

        assert result["extracted_value"] == "john@test.com"
        assert result["current_field"] == "email"


class TestValidateNode:
    """Tests for validate_node."""

    @pytest.mark.asyncio
    async def test_validate_valid_email(self, agent):
        """Test validation passes for valid email."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        graph_state = create_initial_state(state, "john@example.com")
        graph_state["extracted_value"] = "john@example.com"
        graph_state["current_field"] = "email"

        result = await validate_node(graph_state, agent)

        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_validate_invalid_email(self, agent):
        """Test validation fails for invalid email."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        graph_state = create_initial_state(state, "not-an-email")
        graph_state["extracted_value"] = "not-an-email"
        graph_state["current_field"] = "email"

        result = await validate_node(graph_state, agent)

        assert result["is_valid"] is False

    @pytest.mark.asyncio
    async def test_validate_no_extracted_value(self, agent):
        """Test validation fails when no value extracted."""
        state = ConversationState()
        graph_state = create_initial_state(state, "hello")
        graph_state["extracted_value"] = None
        graph_state["current_field"] = "full_name"

        result = await validate_node(graph_state, agent)

        assert result["is_valid"] is False


class TestPromptNextNode:
    """Tests for prompt_next_node."""

    @pytest.mark.asyncio
    async def test_prompt_for_next_field(self, agent, mock_llm_provider):
        """Test prompting for next field."""
        state = ConversationState()
        graph_state = create_initial_state(state, "hello")
        graph_state["is_off_topic"] = False
        graph_state["extracted_value"] = None

        mock_llm_provider.ainvoke = AsyncMock(return_value="What is your full name?")

        result = await prompt_next_node(graph_state, agent)

        assert result["response"] == "What is your full name?"

    @pytest.mark.asyncio
    async def test_prompt_redirect_off_topic(self, agent, mock_llm_provider):
        """Test prompting redirects off-topic users."""
        state = ConversationState()
        graph_state = create_initial_state(state, "What's the weather?")
        graph_state["is_off_topic"] = True

        mock_llm_provider.ainvoke = AsyncMock(
            return_value="I appreciate your question! Let's continue - what is your full name?"
        )

        result = await prompt_next_node(graph_state, agent)

        assert "name" in result["response"].lower() or "continue" in result["response"].lower()


class TestEscalateNode:
    """Tests for escalate_node."""

    @pytest.mark.asyncio
    async def test_escalate_marks_state(self, agent):
        """Test escalation marks conversation state."""
        state = ConversationState()
        graph_state = create_initial_state(state, "I need a human agent")
        graph_state["should_escalate"] = True
        graph_state["escalation_reason"] = "User requested human agent"
        graph_state["metadata"]["escalation_policy_id"] = "policy_0_keyword"

        result = await escalate_node(graph_state, agent)

        assert result["conversation"].escalation_triggered is True
        assert "human agent" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_escalate_generates_response(self, agent):
        """Test escalation generates appropriate response."""
        state = ConversationState()
        graph_state = create_initial_state(state, "I need help")
        graph_state["should_escalate"] = True
        graph_state["escalation_reason"] = "User needs help"

        result = await escalate_node(graph_state, agent)

        assert result["response"] != ""
        assert "connecting" in result["response"].lower()


class TestCompleteNode:
    """Tests for complete_node."""

    @pytest.mark.asyncio
    async def test_complete_generates_thank_you(self, agent, mock_llm_provider):
        """Test completion generates thank you message."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)
        graph_state = create_initial_state(state, "that's all")

        mock_llm_provider.ainvoke = AsyncMock(return_value="Thank you for your information!")

        result = await complete_node(graph_state, agent)

        assert result["response"] == "Thank you for your information!"
        assert result["conversation"].status.value == "completed"

    @pytest.mark.asyncio
    async def test_complete_marks_state_completed(self, agent, mock_llm_provider):
        """Test completion marks state as completed."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)
        graph_state = create_initial_state(state, "done")

        mock_llm_provider.ainvoke = AsyncMock(return_value="All done!")

        result = await complete_node(graph_state, agent)

        assert result["conversation"].status.value == "completed"
