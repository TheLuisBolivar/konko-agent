"""Tests for escalation policy handlers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from agent_core.escalation.handlers import (
    CompletionPolicyHandler,
    KeywordPolicyHandler,
    LLMIntentPolicyHandler,
    SentimentPolicyHandler,
    TimeoutPolicyHandler,
)
from agent_runtime import ConversationState, MessageRole


@pytest.fixture
def conversation_state():
    """Create a basic conversation state for testing."""
    state = ConversationState()
    state.add_message(MessageRole.AGENT, "Hello! How can I help you?")
    return state


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock()
    provider.ainvoke = AsyncMock(return_value="0.5")
    return provider


class TestKeywordPolicyHandler:
    """Tests for KeywordPolicyHandler."""

    @pytest.mark.asyncio
    async def test_keyword_match_triggers_escalation(self, conversation_state):
        """Test that matching keyword triggers escalation."""
        handler = KeywordPolicyHandler()
        config = {"keywords": ["help", "human", "agent"]}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I need help please",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_id == "test_policy_1"
        assert result.policy_type == "keyword"
        assert result.reason == "User requested help"
        assert result.metadata["matched_keyword"] == "help"

    @pytest.mark.asyncio
    async def test_no_keyword_match_returns_none(self, conversation_state):
        """Test that no matching keyword returns None."""
        handler = KeywordPolicyHandler()
        config = {"keywords": ["urgent", "emergency"]}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="This is a normal message",
            config=config,
            policy_id="test_policy_1",
            reason="Urgent request",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, conversation_state):
        """Test case insensitive keyword matching."""
        handler = KeywordPolicyHandler()
        config = {"keywords": ["HELP"], "case_sensitive": False}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="i need help",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is not None
        assert result.should_escalate is True

    @pytest.mark.asyncio
    async def test_case_sensitive_matching(self, conversation_state):
        """Test case sensitive keyword matching when enabled."""
        handler = KeywordPolicyHandler()
        config = {"keywords": ["HELP"], "case_sensitive": True}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="i need help",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_whole_word_matching(self, conversation_state):
        """Test whole word matching option."""
        handler = KeywordPolicyHandler()
        config = {"keywords": ["help"], "match_whole_word": True}

        # Should not match "helpful"
        result = await handler.evaluate(
            state=conversation_state,
            user_message="That's very helpful",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is None

        # Should match "help" as whole word
        result = await handler.evaluate(
            state=conversation_state,
            user_message="I need help now",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is not None

    @pytest.mark.asyncio
    async def test_empty_keywords_returns_none(self, conversation_state):
        """Test empty keywords list returns None."""
        handler = KeywordPolicyHandler()
        config = {"keywords": []}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I need help",
            config=config,
            policy_id="test_policy_1",
            reason="User requested help",
        )

        assert result is None


class TestTimeoutPolicyHandler:
    """Tests for TimeoutPolicyHandler."""

    @pytest.mark.asyncio
    async def test_timeout_exceeded_triggers_escalation(self):
        """Test that exceeding timeout triggers escalation."""
        handler = TimeoutPolicyHandler()
        config = {"max_duration_seconds": 60}

        # Create state with old start time
        state = ConversationState()
        state.started_at = datetime.now(timezone.utc) - timedelta(seconds=120)

        result = await handler.evaluate(
            state=state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_2",
            reason="Conversation timeout",
        )

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_type == "timeout"
        assert result.metadata["max_duration_seconds"] == 60

    @pytest.mark.asyncio
    async def test_within_timeout_returns_none(self, conversation_state):
        """Test that within timeout returns None."""
        handler = TimeoutPolicyHandler()
        config = {"max_duration_seconds": 300}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_2",
            reason="Conversation timeout",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_max_duration_returns_none(self, conversation_state):
        """Test that missing max_duration_seconds returns None."""
        handler = TimeoutPolicyHandler()
        config = {}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_2",
            reason="Conversation timeout",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_max_duration_returns_none(self, conversation_state):
        """Test that invalid max_duration_seconds returns None."""
        handler = TimeoutPolicyHandler()
        config = {"max_duration_seconds": "invalid"}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_2",
            reason="Conversation timeout",
        )

        assert result is None


class TestCompletionPolicyHandler:
    """Tests for CompletionPolicyHandler."""

    @pytest.mark.asyncio
    async def test_all_fields_collected_triggers_escalation(self):
        """Test that all fields collected triggers escalation."""
        handler = CompletionPolicyHandler()
        config = {
            "required_fields": ["name", "email"],
            "escalate_when_complete": True,
        }

        state = ConversationState()
        state.update_field_value("name", "John Doe", True)
        state.update_field_value("email", "john@example.com", True)

        result = await handler.evaluate(
            state=state,
            user_message="Done",
            config=config,
            policy_id="test_policy_3",
            reason="All fields collected",
        )

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_type == "completion"

    @pytest.mark.asyncio
    async def test_missing_fields_returns_none_when_escalate_when_complete(self):
        """Test missing fields returns None when escalate_when_complete is True."""
        handler = CompletionPolicyHandler()
        config = {
            "required_fields": ["name", "email", "phone"],
            "escalate_when_complete": True,
        }

        state = ConversationState()
        state.update_field_value("name", "John Doe", True)

        result = await handler.evaluate(
            state=state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_3",
            reason="All fields collected",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_missing_fields_triggers_when_escalate_when_incomplete(self):
        """Test missing fields triggers when escalate_when_complete is False."""
        handler = CompletionPolicyHandler()
        config = {
            "required_fields": ["name", "email", "phone"],
            "escalate_when_complete": False,
        }

        state = ConversationState()
        state.update_field_value("name", "John Doe", True)

        result = await handler.evaluate(
            state=state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_3",
            reason="Fields missing",
        )

        assert result is not None
        assert result.should_escalate is True
        assert "email" in result.metadata["missing_fields"]
        assert "phone" in result.metadata["missing_fields"]

    @pytest.mark.asyncio
    async def test_empty_required_fields_returns_none(self, conversation_state):
        """Test empty required_fields list returns None."""
        handler = CompletionPolicyHandler()
        config = {"required_fields": []}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_3",
            reason="All fields collected",
        )

        assert result is None


class TestSentimentPolicyHandler:
    """Tests for SentimentPolicyHandler."""

    @pytest.mark.asyncio
    async def test_negative_sentiment_triggers_escalation(
        self, conversation_state, mock_llm_provider
    ):
        """Test that negative sentiment triggers escalation."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="0.85")
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="This is terrible! I'm very frustrated!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_type == "sentiment"
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_positive_sentiment_returns_none(self, conversation_state, mock_llm_provider):
        """Test that positive sentiment returns None."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="0.2")
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="This is great, thank you!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_llm_provider_returns_none(self, conversation_state):
        """Test that missing LLM provider returns None."""
        handler = SentimentPolicyHandler(llm_provider=None)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I'm angry!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_llm_error_returns_none(self, conversation_state, mock_llm_provider):
        """Test that LLM error returns None."""
        mock_llm_provider.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I'm angry!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_sentiment_response_returns_none(
        self, conversation_state, mock_llm_provider
    ):
        """Test that invalid LLM response returns None."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="not a number")
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Hello",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_sentiment_score_clamped(self, conversation_state, mock_llm_provider):
        """Test that sentiment score is clamped to valid range."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="1.5")
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Very angry!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is not None
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_sentiment_with_conversation_history(self, mock_llm_provider):
        """Test sentiment analysis includes conversation history."""
        from agent_runtime import MessageRole

        mock_llm_provider.ainvoke = AsyncMock(return_value="0.9")
        handler = SentimentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"threshold": 0.7, "include_history": True}

        # Create state with message history
        state = ConversationState()
        state.add_message(MessageRole.AGENT, "Hello, how can I help?")
        state.add_message(MessageRole.USER, "I've been waiting forever")
        state.add_message(MessageRole.AGENT, "I apologize for the wait")

        result = await handler.evaluate(
            state=state,
            user_message="This is unacceptable!",
            config=config,
            policy_id="test_policy_4",
            reason="Negative sentiment detected",
        )

        assert result is not None
        assert result.should_escalate is True
        # Verify the prompt included context (check the call)
        call_args = mock_llm_provider.ainvoke.call_args[0][0]
        assert "context" in call_args.lower() or "user:" in call_args.lower()


class TestLLMIntentPolicyHandler:
    """Tests for LLMIntentPolicyHandler."""

    @pytest.mark.asyncio
    async def test_detected_intent_triggers_escalation(self, conversation_state, mock_llm_provider):
        """Test that detected intent triggers escalation."""
        mock_llm_provider.ainvoke = AsyncMock(
            return_value="DETECTED: user wants to speak with a human\nCONFIDENCE: 0.95"
        )
        handler = LLMIntentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"confidence_threshold": 0.8}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I want to talk to a real person",
            config=config,
            policy_id="test_policy_5",
            reason="User requested human agent",
        )

        assert result is not None
        assert result.should_escalate is True
        assert result.policy_type == "llm_intent"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_no_intent_detected_returns_none(self, conversation_state, mock_llm_provider):
        """Test that no detected intent returns None."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="DETECTED: NONE\nCONFIDENCE: 0.0")
        handler = LLMIntentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"confidence_threshold": 0.8}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="What are your business hours?",
            config=config,
            policy_id="test_policy_5",
            reason="User requested human agent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_low_confidence_returns_none(self, conversation_state, mock_llm_provider):
        """Test that low confidence intent returns None."""
        mock_llm_provider.ainvoke = AsyncMock(
            return_value="DETECTED: user wants to speak with a human\nCONFIDENCE: 0.5"
        )
        handler = LLMIntentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"confidence_threshold": 0.8}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="Maybe I should talk to someone?",
            config=config,
            policy_id="test_policy_5",
            reason="User requested human agent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_no_llm_provider_returns_none(self, conversation_state):
        """Test that missing LLM provider returns None."""
        handler = LLMIntentPolicyHandler(llm_provider=None)
        config = {"confidence_threshold": 0.8}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I want a human",
            config=config,
            policy_id="test_policy_5",
            reason="User requested human agent",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_custom_intents_used(self, conversation_state, mock_llm_provider):
        """Test that custom intents are used in evaluation."""
        mock_llm_provider.ainvoke = AsyncMock(return_value="DETECTED: NONE\nCONFIDENCE: 0.0")
        handler = LLMIntentPolicyHandler(llm_provider=mock_llm_provider)
        config = {
            "intents": ["user wants a refund", "user is cancelling"],
            "confidence_threshold": 0.8,
        }

        await handler.evaluate(
            state=conversation_state,
            user_message="I want my money back",
            config=config,
            policy_id="test_policy_5",
            reason="Custom intent detected",
        )

        # Verify the prompt included custom intents
        call_args = mock_llm_provider.ainvoke.call_args
        prompt = call_args[0][0]
        assert "user wants a refund" in prompt
        assert "user is cancelling" in prompt

    @pytest.mark.asyncio
    async def test_llm_error_returns_none(self, conversation_state, mock_llm_provider):
        """Test that LLM error returns None."""
        mock_llm_provider.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
        handler = LLMIntentPolicyHandler(llm_provider=mock_llm_provider)
        config = {"confidence_threshold": 0.8}

        result = await handler.evaluate(
            state=conversation_state,
            user_message="I want a human",
            config=config,
            policy_id="test_policy_5",
            reason="User requested human agent",
        )

        assert result is None
