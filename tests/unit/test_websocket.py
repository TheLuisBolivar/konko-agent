"""Tests for WebSocket functionality."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from agent_api import create_app
from agent_api.app import app_state
from agent_api.websocket import ConnectionManager
from agent_config import AgentConfig, AgentPersonality, FieldConfig, Formality, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from agent_core import LLMProvider


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


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh connection manager for each test."""
        return ConnectionManager()

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager.active_connections == {}

    @pytest.mark.asyncio
    async def test_connect(self, manager):
        """Test connecting a WebSocket."""
        mock_ws = AsyncMock()
        await manager.connect(mock_ws, "test-session")

        assert "test-session" in manager.active_connections
        mock_ws.accept.assert_called_once()

    def test_disconnect(self, manager):
        """Test disconnecting a WebSocket."""
        manager.active_connections["test-session"] = Mock()
        manager.disconnect("test-session")

        assert "test-session" not in manager.active_connections

    def test_disconnect_nonexistent(self, manager):
        """Test disconnecting a non-existent session."""
        manager.disconnect("nonexistent")
        assert "nonexistent" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_send_message(self, manager):
        """Test sending a message to a connection."""
        mock_ws = AsyncMock()
        manager.active_connections["test-session"] = mock_ws

        await manager.send_message("test-session", {"type": "test"})

        mock_ws.send_json.assert_called_once_with({"type": "test"})

    @pytest.mark.asyncio
    async def test_send_message_no_connection(self, manager):
        """Test sending to a non-existent connection does nothing."""
        await manager.send_message("nonexistent", {"type": "test"})

    def test_is_connected_true(self, manager):
        """Test is_connected returns True for active connections."""
        manager.active_connections["test-session"] = Mock()
        assert manager.is_connected("test-session") is True

    def test_is_connected_false(self, manager):
        """Test is_connected returns False for non-existent connections."""
        assert manager.is_connected("nonexistent") is False


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint."""

    def test_websocket_connect_without_agent(self, reset_app_state):
        """Test WebSocket connection when agent not configured."""
        app = create_app()
        client = TestClient(app)

        with pytest.raises(Exception):
            with client.websocket_connect("/ws") as websocket:
                pass

    def test_websocket_connect_with_agent(self, basic_config, mock_llm_provider, reset_app_state):
        """Test WebSocket connection with configured agent."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "session_id" in data
            assert "greeting" in data
            assert data["status"] == "active"

    def test_websocket_ping_pong(self, basic_config, mock_llm_provider, reset_app_state):
        """Test WebSocket ping/pong."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()

            websocket.send_json({"type": "ping"})
            response = websocket.receive_json()
            assert response["type"] == "pong"

    def test_websocket_send_message(self, basic_config, mock_llm_provider, reset_app_state):
        """Test sending a message via WebSocket."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        mock_llm_provider.ainvoke = AsyncMock(side_effect=["John Doe", "What's your email?"])
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json()

            websocket.send_json({"type": "message", "content": "My name is John"})
            response = websocket.receive_json()

            assert response["type"] == "response"
            assert "content" in response
            assert "status" in response
            assert "collected_data" in response

    def test_websocket_full_conversation(self, basic_config, mock_llm_provider, reset_app_state):
        """Test complete conversation via WebSocket."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        mock_llm_provider.ainvoke = AsyncMock(
            side_effect=[
                "John Doe",
                "What's your email?",
                "john@example.com",
                "Thank you!",
            ]
        )
        client = TestClient(app)

        with client.websocket_connect("/ws") as websocket:
            connected = websocket.receive_json()
            assert connected["type"] == "connected"

            websocket.send_json({"type": "message", "content": "John Doe"})
            response1 = websocket.receive_json()
            assert response1["type"] == "response"
            assert "full_name" in response1["collected_data"]

            websocket.send_json({"type": "message", "content": "john@example.com"})
            response2 = websocket.receive_json()
            assert response2["type"] == "response"
            assert response2["status"] == "completed"

            completed = websocket.receive_json()
            assert completed["type"] == "completed"
            assert "email" in completed["collected_data"]


class TestWebSocketWithSession:
    """Tests for WebSocket with existing session."""

    def test_websocket_with_existing_session(
        self, basic_config, mock_llm_provider, reset_app_state
    ):
        """Test continuing existing session via WebSocket."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        client = TestClient(app)

        start_response = client.post("/conversations")
        session_id = start_response.json()["session_id"]

        with client.websocket_connect(f"/ws/{session_id}") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_websocket_with_invalid_session(self, basic_config, mock_llm_provider, reset_app_state):
        """Test WebSocket with non-existent session creates new one."""
        app = create_app(config=basic_config)
        app_state.agent._llm_provider = mock_llm_provider
        client = TestClient(app)

        with client.websocket_connect("/ws/nonexistent-session") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] != "nonexistent-session"
