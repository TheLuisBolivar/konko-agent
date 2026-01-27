"""Tests for graph edge routing functions."""

from unittest.mock import Mock

import pytest
from agent_config import AgentConfig, AgentPersonality, FieldConfig, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import ConversationalAgent, LLMProvider
from agent_core.graph.edges import (
    route_after_correction_check,
    route_after_escalation_check,
    route_after_off_topic_check,
    route_after_validate,
    should_continue_after_complete,
    should_continue_after_escalate,
    should_continue_after_prompt,
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
    return provider


@pytest.fixture
def agent(basic_config, store, mock_llm_provider):
    """Create an agent for testing."""
    return ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)


class TestRouteAfterEscalationCheck:
    """Tests for route_after_escalation_check."""

    def test_routes_to_escalate_when_should_escalate(self, agent):
        """Test routing to escalate when escalation detected."""
        state = ConversationState()
        graph_state = create_initial_state(state, "Help me")
        graph_state["should_escalate"] = True

        result = route_after_escalation_check(graph_state, agent)

        assert result == "escalate"

    def test_routes_to_check_correction_when_no_escalation(self, agent):
        """Test routing to check_correction when no escalation."""
        state = ConversationState()
        graph_state = create_initial_state(state, "My name is John")
        graph_state["should_escalate"] = False

        result = route_after_escalation_check(graph_state, agent)

        assert result == "check_correction"


class TestRouteAfterCorrectionCheck:
    """Tests for route_after_correction_check."""

    def test_routes_to_extract_field_when_correction(self, agent):
        """Test routing to extract_field when correction detected."""
        state = ConversationState()
        graph_state = create_initial_state(state, "No, my email is test@test.com")
        graph_state["is_correction"] = True

        result = route_after_correction_check(graph_state, agent)

        assert result == "extract_field"

    def test_routes_to_check_off_topic_when_no_correction(self, agent):
        """Test routing to check_off_topic when no correction."""
        state = ConversationState()
        graph_state = create_initial_state(state, "Hello")
        graph_state["is_correction"] = False

        result = route_after_correction_check(graph_state, agent)

        assert result == "check_off_topic"


class TestRouteAfterOffTopicCheck:
    """Tests for route_after_off_topic_check."""

    def test_routes_to_complete_when_all_fields_collected(self, agent):
        """Test routing to complete when all fields collected."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)
        graph_state = create_initial_state(state, "That's all")
        graph_state["is_off_topic"] = False

        result = route_after_off_topic_check(graph_state, agent)

        assert result == "complete"

    def test_routes_to_prompt_next_when_off_topic(self, agent):
        """Test routing to prompt_next when off-topic."""
        state = ConversationState()
        graph_state = create_initial_state(state, "What's the weather?")
        graph_state["is_off_topic"] = True

        result = route_after_off_topic_check(graph_state, agent)

        assert result == "prompt_next"

    def test_routes_to_extract_field_when_on_topic(self, agent):
        """Test routing to extract_field when on-topic with fields remaining."""
        state = ConversationState()
        graph_state = create_initial_state(state, "My name is John")
        graph_state["is_off_topic"] = False

        result = route_after_off_topic_check(graph_state, agent)

        assert result == "extract_field"


class TestRouteAfterValidate:
    """Tests for route_after_validate."""

    def test_routes_to_complete_when_all_collected(self, agent):
        """Test routing to complete when all fields collected."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "123-456-7890", True)
        graph_state = create_initial_state(state, "done")
        graph_state["is_valid"] = True

        result = route_after_validate(graph_state, agent)

        assert result == "complete"

    def test_routes_to_prompt_next_when_invalid(self, agent):
        """Test routing to prompt_next when validation fails."""
        state = ConversationState()
        graph_state = create_initial_state(state, "invalid-email")
        graph_state["is_valid"] = False
        graph_state["current_field"] = "email"

        result = route_after_validate(graph_state, agent)

        assert result == "prompt_next"

    def test_routes_to_prompt_next_when_more_fields(self, agent):
        """Test routing to prompt_next when more fields to collect."""
        state = ConversationState()
        state.update_field_value("full_name", "John Doe", True)
        graph_state = create_initial_state(state, "john@example.com")
        graph_state["is_valid"] = True

        result = route_after_validate(graph_state, agent)

        assert result == "prompt_next"


class TestTerminalRoutes:
    """Tests for terminal routing functions."""

    def test_should_continue_after_prompt_returns_end(self, agent):
        """Test prompt node always ends."""
        state = ConversationState()
        graph_state = create_initial_state(state, "hello")

        result = should_continue_after_prompt(graph_state, agent)

        assert result == "__end__"

    def test_should_continue_after_escalate_returns_end(self, agent):
        """Test escalate node always ends."""
        state = ConversationState()
        graph_state = create_initial_state(state, "I need help")

        result = should_continue_after_escalate(graph_state, agent)

        assert result == "__end__"

    def test_should_continue_after_complete_returns_end(self, agent):
        """Test complete node always ends."""
        state = ConversationState()
        graph_state = create_initial_state(state, "done")

        result = should_continue_after_complete(graph_state, agent)

        assert result == "__end__"
