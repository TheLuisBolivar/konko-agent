"""Tests for FastAPI Application Factory."""

import pytest
from fastapi.testclient import TestClient

from agent_api import create_app
from agent_api.app import AppState, app_state, get_app_state
from agent_config import AgentConfig, AgentPersonality, FieldConfig, Formality, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone


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
def reset_app_state():
    """Reset application state before and after tests."""
    # Reset before test
    app_state.agent = None
    app_state.store = None
    app_state.config = None
    yield
    # Reset after test
    app_state.agent = None
    app_state.store = None
    app_state.config = None


class TestCreateApp:
    """Tests for create_app factory function."""

    def test_create_app_without_config(self, reset_app_state):
        """Test creating app without configuration."""
        app = create_app()

        assert app is not None
        assert app.title == "Konko AI Conversational Agent"
        assert app.version == "0.1.0"

    def test_create_app_with_config(self, basic_config, reset_app_state):
        """Test creating app with configuration."""
        app = create_app(config=basic_config)

        assert app is not None
        assert app_state.config == basic_config
        assert app_state.agent is not None

    def test_create_app_initializes_store(self, reset_app_state):
        """Test that create_app initializes the state store."""
        app = create_app()

        assert app_state.store is not None

    def test_create_app_with_cors_origins(self, reset_app_state):
        """Test creating app with custom CORS origins."""
        origins = ["http://localhost:3000", "https://example.com"]
        app = create_app(cors_origins=origins)

        # Verify CORS middleware is added
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_without_agent(self, reset_app_state):
        """Test health check when agent is not configured."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert data["agent_configured"] is False

    def test_health_check_with_agent(self, basic_config, reset_app_state):
        """Test health check when agent is configured."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["agent_configured"] is True


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_endpoint(self, reset_app_state):
        """Test root endpoint returns welcome message."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Konko AI" in data["message"]
        assert data["version"] == "0.1.0"
        assert data["docs_url"] == "/docs"


class TestAppState:
    """Tests for AppState class."""

    def test_app_state_initialization(self):
        """Test AppState initializes with None values."""
        state = AppState()

        assert state.agent is None
        assert state.store is None
        assert state.config is None

    def test_get_app_state_returns_singleton(self, reset_app_state):
        """Test get_app_state returns the module-level state."""
        state = get_app_state()

        assert state is app_state


class TestOpenAPIDocumentation:
    """Tests for OpenAPI documentation."""

    def test_openapi_endpoint(self, reset_app_state):
        """Test OpenAPI schema is available."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert data["info"]["title"] == "Konko AI Conversational Agent"
        assert data["info"]["version"] == "0.1.0"

    def test_docs_endpoint(self, reset_app_state):
        """Test Swagger UI docs are available."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/docs")

        assert response.status_code == 200
