"""Tests for API routes."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from agent_api import create_app
from agent_api.app import app_state
from agent_config import AgentConfig, AgentPersonality, FieldConfig, Formality, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import LLMProvider
from agent_runtime import ConversationState, MessageRole


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
        ],
    )


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock(spec=LLMProvider)
    provider.invoke = Mock(return_value="Test response")
    provider.ainvoke = AsyncMock(return_value="Test response")
    return provider


@pytest.fixture
def reset_app_state():
    """Reset application state before and after tests."""
    app_state.agent = None
    app_state.store = None
    app_state.config = None
    yield
    app_state.agent = None
    app_state.store = None
    app_state.config = None


class TestStartConversation:
    """Tests for POST /conversations endpoint."""

    def test_start_conversation_success(self, basic_config, reset_app_state):
        """Test successfully starting a conversation."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.post("/conversations")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["greeting"] == basic_config.greeting
        assert data["status"] == "active"

    def test_start_conversation_no_agent(self, reset_app_state):
        """Test starting conversation when agent not configured."""
        app = create_app()
        client = TestClient(app)

        response = client.post("/conversations")

        assert response.status_code == 503
        data = response.json()
        assert "not configured" in data["detail"].lower()


class TestSendMessage:
    """Tests for POST /conversations/{session_id}/messages endpoint."""

    def test_send_message_success(self, basic_config, mock_llm_provider, reset_app_state):
        """Test successfully sending a message."""
        app = create_app(config=basic_config)
        # Inject mock LLM provider
        app_state.agent._llm_provider = mock_llm_provider
        mock_llm_provider.ainvoke = AsyncMock(side_effect=["John Doe", "Great! What's your email?"])
        client = TestClient(app)

        # Start conversation first
        start_response = client.post("/conversations")
        session_id = start_response.json()["session_id"]

        # Send message
        response = client.post(
            f"/conversations/{session_id}/messages",
            json={"content": "My name is John Doe"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "response" in data
        assert data["status"] in ["active", "completed"]

    def test_send_message_session_not_found(self, basic_config, reset_app_state):
        """Test sending message to non-existent session."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.post(
            "/conversations/nonexistent-session/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_send_message_no_agent(self, reset_app_state):
        """Test sending message when agent not configured."""
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/conversations/any-session/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 503


class TestGetConversation:
    """Tests for GET /conversations/{session_id} endpoint."""

    def test_get_conversation_success(self, basic_config, reset_app_state):
        """Test successfully getting conversation state."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        # Start conversation first
        start_response = client.post("/conversations")
        session_id = start_response.json()["session_id"]

        # Get conversation
        response = client.get(f"/conversations/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["status"] == "active"
        assert "messages" in data
        assert len(data["messages"]) == 1  # Greeting message
        assert "started_at" in data
        assert "collected_data" in data

    def test_get_conversation_not_found(self, basic_config, reset_app_state):
        """Test getting non-existent conversation."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.get("/conversations/nonexistent-session")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestDeleteConversation:
    """Tests for DELETE /conversations/{session_id} endpoint."""

    def test_delete_conversation_success(self, basic_config, reset_app_state):
        """Test successfully deleting a conversation."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        # Start conversation first
        start_response = client.post("/conversations")
        session_id = start_response.json()["session_id"]

        # Delete conversation
        response = client.delete(f"/conversations/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

        # Verify it's deleted
        get_response = client.get(f"/conversations/{session_id}")
        assert get_response.status_code == 404

    def test_delete_conversation_not_found(self, basic_config, reset_app_state):
        """Test deleting non-existent conversation."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.delete("/conversations/nonexistent-session")

        assert response.status_code == 404


class TestConversationFlow:
    """Integration tests for full conversation flow."""

    def test_full_conversation_flow(self, basic_config, mock_llm_provider, reset_app_state):
        """Test complete conversation from start to finish."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        client = TestClient(app)

        # Set up mock responses for the full flow
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "John Doe",  # Extract name
                "Great! What's your email?",  # Ask for email
                "john@example.com",  # Extract email
                "Thank you! All information collected.",  # Completion
            ]
        )

        # 1. Start conversation
        start_response = client.post("/conversations")
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        # 2. Send name
        msg1_response = client.post(
            f"/conversations/{session_id}/messages",
            json={"content": "My name is John Doe"},
        )
        assert msg1_response.status_code == 200
        data1 = msg1_response.json()
        assert "full_name" in data1["collected_data"]

        # 3. Send email
        msg2_response = client.post(
            f"/conversations/{session_id}/messages",
            json={"content": "My email is john@example.com"},
        )
        assert msg2_response.status_code == 200
        data2 = msg2_response.json()
        assert data2["status"] == "completed"
        assert "email" in data2["collected_data"]

        # 4. Verify final state
        get_response = client.get(f"/conversations/{session_id}")
        assert get_response.status_code == 200
        final_data = get_response.json()
        assert final_data["status"] == "completed"
        assert len(final_data["collected_data"]) == 2
