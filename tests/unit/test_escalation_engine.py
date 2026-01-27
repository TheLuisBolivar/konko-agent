"""Tests for EscalationEngine module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from agent_config import AgentConfig, AgentPersonality, EscalationPolicy, FieldConfig, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_core import LLMProvider
from agent_core.escalation import EscalationEngine, EscalationResult
from agent_runtime import ConversationState, MessageRole


@pytest.fixture
def basic_config():
    """Create a basic agent configuration for testing."""
    return AgentConfig(
        personality=AgentPersonality(),
        llm=LLMConfig(
            provider=LLMProviderEnum.OPENAI,
            model_name="gpt-3.5-turbo",
        ),
        greeting="Hello!",
        fields=[
            FieldConfig(name="name", field_type="text", required=True),
            FieldConfig(name="email", field_type="email", required=True),
        ],
        escalation_policies=[],
    )


@pytest.fixture
def config_with_keyword_policy(basic_config):
    """Create config with keyword escalation policy."""
    basic_config.escalation_policies = [
        EscalationPolicy(
            enabled=True,
            reason="User requested help",
            policy_type="keyword",
            config={"keywords": ["help", "human", "agent"]},
        )
    ]
    return basic_config


@pytest.fixture
def config_with_multiple_policies(basic_config):
    """Create config with multiple escalation policies."""
    basic_config.escalation_policies = [
        EscalationPolicy(
            enabled=True,
            reason="User requested help",
            policy_type="keyword",
            config={"keywords": ["help", "human"]},
        ),
        EscalationPolicy(
            enabled=True,
            reason="Conversation timeout",
            policy_type="timeout",
            config={"max_duration_seconds": 300},
        ),
        EscalationPolicy(
            enabled=True,
            reason="Negative sentiment",
            policy_type="sentiment",
            config={"threshold": 0.7},
        ),
    ]
    return basic_config


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock(spec=LLMProvider)
    provider.ainvoke = AsyncMock(return_value="0.3")
    return provider


@pytest.fixture
def conversation_state():
    """Create a basic conversation state for testing."""
    state = ConversationState()
    state.add_message(MessageRole.AGENT, "Hello! How can I help?")
    return state


class TestEscalationEngineInit:
    """Tests for EscalationEngine initialization."""

    def test_engine_initialization(self, basic_config, mock_llm_provider):
        """Test basic engine initialization."""
        engine = EscalationEngine(basic_config, mock_llm_provider)

        assert engine.config == basic_config
        assert engine.llm_provider == mock_llm_provider

    def test_engine_initializes_all_handlers(self, basic_config, mock_llm_provider):
        """Test that engine initializes all handler types."""
        engine = EscalationEngine(basic_config, mock_llm_provider)

        assert "keyword" in engine._handlers
        assert "timeout" in engine._handlers
        assert "completion" in engine._handlers
        assert "sentiment" in engine._handlers
        assert "llm_intent" in engine._handlers

    def test_engine_without_llm_provider(self, basic_config):
        """Test engine initialization without LLM provider."""
        engine = EscalationEngine(basic_config, llm_provider=None)

        assert engine.llm_provider is None
        # LLM-dependent handlers should still be created but won't work
        assert "sentiment" in engine._handlers
        assert "llm_intent" in engine._handlers


class TestHasPolicies:
    """Tests for has_policies method."""

    def test_has_policies_returns_false_when_empty(self, basic_config):
        """Test has_policies returns False when no policies configured."""
        engine = EscalationEngine(basic_config)

        assert engine.has_policies() is False

    def test_has_policies_returns_true_when_enabled(self, config_with_keyword_policy):
        """Test has_policies returns True when enabled policies exist."""
        engine = EscalationEngine(config_with_keyword_policy)

        assert engine.has_policies() is True

    def test_has_policies_returns_false_when_all_disabled(self, basic_config):
        """Test has_policies returns False when all policies are disabled."""
        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=False,
                reason="Disabled policy",
                policy_type="keyword",
                config={"keywords": ["help"]},
            )
        ]
        engine = EscalationEngine(basic_config)

        assert engine.has_policies() is False


class TestEvaluate:
    """Tests for evaluate method."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_none_when_no_policies(self, basic_config, conversation_state):
        """Test evaluate returns None when no policies configured."""
        engine = EscalationEngine(basic_config)

        result = await engine.evaluate(conversation_state, "Hello")

        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_returns_result_on_match(
        self, config_with_keyword_policy, conversation_state
    ):
        """Test evaluate returns result when policy matches."""
        engine = EscalationEngine(config_with_keyword_policy)

        result = await engine.evaluate(conversation_state, "I need help")

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_type == "keyword"
        assert result.reason == "User requested help"

    @pytest.mark.asyncio
    async def test_evaluate_returns_none_on_no_match(
        self, config_with_keyword_policy, conversation_state
    ):
        """Test evaluate returns None when no policy matches."""
        engine = EscalationEngine(config_with_keyword_policy)

        result = await engine.evaluate(conversation_state, "What are your hours?")

        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_skips_disabled_policies(self, basic_config, conversation_state):
        """Test evaluate skips disabled policies."""
        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=False,
                reason="Disabled",
                policy_type="keyword",
                config={"keywords": ["help"]},
            )
        ]
        engine = EscalationEngine(basic_config)

        result = await engine.evaluate(conversation_state, "I need help")

        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_priority_order(
        self, config_with_multiple_policies, conversation_state, mock_llm_provider
    ):
        """Test that policies are evaluated in priority order."""
        engine = EscalationEngine(config_with_multiple_policies, mock_llm_provider)

        # This should match keyword first (highest priority)
        result = await engine.evaluate(conversation_state, "I need help")

        assert result is not None
        assert result.policy_type == "keyword"

    @pytest.mark.asyncio
    async def test_evaluate_stops_on_first_match(
        self, basic_config, conversation_state, mock_llm_provider
    ):
        """Test that evaluate stops on first matching policy."""
        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=True,
                reason="First match",
                policy_type="keyword",
                config={"keywords": ["help"]},
            ),
            EscalationPolicy(
                enabled=True,
                reason="Second match",
                policy_type="keyword",
                config={"keywords": ["help"]},
            ),
        ]
        engine = EscalationEngine(basic_config, mock_llm_provider)

        result = await engine.evaluate(conversation_state, "I need help")

        assert result is not None
        assert result.reason == "First match"


class TestEvaluateAll:
    """Tests for evaluate_all method."""

    @pytest.mark.asyncio
    async def test_evaluate_all_returns_empty_when_no_match(
        self, config_with_keyword_policy, conversation_state
    ):
        """Test evaluate_all returns empty list when no match."""
        engine = EscalationEngine(config_with_keyword_policy)

        results = await engine.evaluate_all(conversation_state, "What time is it?")

        assert results == []

    @pytest.mark.asyncio
    async def test_evaluate_all_returns_all_matches(self, basic_config, conversation_state):
        """Test evaluate_all returns all matching policies."""
        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=True,
                reason="First match",
                policy_type="keyword",
                config={"keywords": ["help"]},
            ),
            EscalationPolicy(
                enabled=True,
                reason="Second match",
                policy_type="keyword",
                config={"keywords": ["need"]},
            ),
        ]
        engine = EscalationEngine(basic_config)

        results = await engine.evaluate_all(conversation_state, "I need help")

        assert len(results) == 2
        reasons = [r.reason for r in results]
        assert "First match" in reasons
        assert "Second match" in reasons


class TestPolicyPriority:
    """Tests for policy priority ordering."""

    @pytest.mark.asyncio
    async def test_keyword_evaluated_before_timeout(self, basic_config, mock_llm_provider):
        """Test keyword is evaluated before timeout."""
        state = ConversationState()
        state.started_at = datetime.now(timezone.utc) - timedelta(seconds=600)

        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=True,
                reason="Timeout",
                policy_type="timeout",
                config={"max_duration_seconds": 300},
            ),
            EscalationPolicy(
                enabled=True,
                reason="Keyword",
                policy_type="keyword",
                config={"keywords": ["help"]},
            ),
        ]
        engine = EscalationEngine(basic_config, mock_llm_provider)

        # Both would match, but keyword has higher priority
        result = await engine.evaluate(state, "I need help")

        assert result is not None
        assert result.policy_type == "keyword"

    @pytest.mark.asyncio
    async def test_timeout_evaluated_before_sentiment(self, basic_config, mock_llm_provider):
        """Test timeout is evaluated before sentiment."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="0.9")
        state = ConversationState()
        state.started_at = datetime.now(timezone.utc) - timedelta(seconds=600)

        basic_config.escalation_policies = [
            EscalationPolicy(
                enabled=True,
                reason="Sentiment",
                policy_type="sentiment",
                config={"threshold": 0.7},
            ),
            EscalationPolicy(
                enabled=True,
                reason="Timeout",
                policy_type="timeout",
                config={"max_duration_seconds": 300},
            ),
        ]
        engine = EscalationEngine(basic_config, mock_llm_provider)

        # Both would match, but timeout has higher priority
        result = await engine.evaluate(state, "This is terrible!")

        assert result is not None
        assert result.policy_type == "timeout"


class TestEscalationResult:
    """Tests for EscalationResult dataclass."""

    def test_escalation_result_creation(self):
        """Test basic EscalationResult creation."""
        result = EscalationResult(
            should_escalate=True,
            policy_id="test_policy",
            policy_type="keyword",
            reason="Test reason",
        )

        assert result.should_escalate is True
        assert result.policy_id == "test_policy"
        assert result.policy_type == "keyword"
        assert result.reason == "Test reason"
        assert result.confidence == 1.0
        assert result.metadata == {}

    def test_escalation_result_with_metadata(self):
        """Test EscalationResult with metadata."""
        result = EscalationResult(
            should_escalate=True,
            policy_id="test_policy",
            policy_type="keyword",
            reason="Test reason",
            confidence=0.85,
            metadata={"matched_keyword": "help"},
        )

        assert result.confidence == 0.85
        assert result.metadata == {"matched_keyword": "help"}

    def test_escalation_result_invalid_confidence_raises(self):
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            EscalationResult(
                should_escalate=True,
                policy_id="test",
                policy_type="keyword",
                reason="Test",
                confidence=1.5,
            )

    def test_escalation_result_handles_none_metadata(self):
        """Test that None metadata is converted to empty dict."""
        result = EscalationResult(
            should_escalate=True,
            policy_id="test",
            policy_type="keyword",
            reason="Test",
            metadata=None,
        )

        assert result.metadata == {}


class TestAgentIntegration:
    """Tests for agent integration with escalation."""

    @pytest.mark.asyncio
    async def test_agent_triggers_escalation(self, config_with_keyword_policy, mock_llm_provider):
        """Test that agent triggers escalation when policy matches."""
        from agent_core import ConversationalAgent
        from agent_runtime import ConversationStatus, StateStore

        store = StateStore()
        agent = ConversationalAgent(
            config_with_keyword_policy, store, llm_provider=mock_llm_provider
        )

        state = agent.start_conversation()

        response, updated_state = await agent.process_message(state, "I need help now")

        assert updated_state.status == ConversationStatus.ESCALATED
        assert updated_state.escalation_triggered is True
        assert updated_state.escalation_reason == "User requested help"

    @pytest.mark.asyncio
    async def test_agent_continues_when_no_escalation(self, basic_config, mock_llm_provider):
        """Test that agent continues normally when no escalation triggered."""
        from agent_core import ConversationalAgent
        from agent_runtime import ConversationStatus, StateStore

        store = StateStore()
        agent = ConversationalAgent(basic_config, store, llm_provider=mock_llm_provider)

        mock_llm_provider.ainvoke = AsyncMock(side_effect=["John Doe", "What's your email?"])

        state = agent.start_conversation()

        response, updated_state = await agent.process_message(state, "My name is John Doe")

        assert updated_state.status == ConversationStatus.ACTIVE
        assert updated_state.escalation_triggered is False
