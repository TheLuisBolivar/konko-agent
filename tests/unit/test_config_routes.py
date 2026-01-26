"""Tests for configuration management routes."""

import os
import tempfile
from pathlib import Path

import pytest
from agent_api import create_app
from agent_api.app import app_state
from agent_config import AgentConfig, AgentPersonality, FieldConfig, Formality, LLMConfig
from agent_config import LLMProvider as LLMProviderEnum
from agent_config import Tone
from fastapi.testclient import TestClient


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
        greeting="Hello! I'm here to help.",
        fields=[
            FieldConfig(name="full_name", field_type="text", required=True),
            FieldConfig(name="email", field_type="email", required=True),
        ],
    )


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


@pytest.fixture
def temp_configs_dir():
    """Create a temporary configs directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test config files
        basic_config = """
greeting: "Hello from basic!"
personality:
  tone: professional
  style: concise
fields:
  - name: name
    field_type: text
    required: true
"""
        advanced_config = """
greeting: "Hello from advanced!"
personality:
  tone: friendly
  style: warm
fields:
  - name: name
    field_type: text
    required: true
  - name: email
    field_type: email
    required: true
"""
        (Path(tmpdir) / "basic_agent.yaml").write_text(basic_config)
        (Path(tmpdir) / "advanced_agent.yaml").write_text(advanced_config)

        # Set environment variable
        old_configs_dir = os.environ.get("CONFIGS_DIR")
        os.environ["CONFIGS_DIR"] = tmpdir

        yield tmpdir

        # Restore environment
        if old_configs_dir:
            os.environ["CONFIGS_DIR"] = old_configs_dir
        else:
            os.environ.pop("CONFIGS_DIR", None)


class TestGetCurrentConfig:
    """Tests for GET /config/current endpoint."""

    def test_get_current_config_not_loaded(self, reset_app_state):
        """Test getting current config when none is loaded."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/config/current")

        assert response.status_code == 200
        data = response.json()
        assert data["loaded"] is False

    def test_get_current_config_loaded(self, basic_config, reset_app_state):
        """Test getting current config when one is loaded."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        response = client.get("/config/current")

        assert response.status_code == 200
        data = response.json()
        assert data["loaded"] is True
        assert data["greeting"] == "Hello! I'm here to help."
        assert len(data["fields"]) == 2
        assert data["personality"]["tone"] == "professional"
        assert data["llm"]["provider"] == "openai"


class TestListConfigs:
    """Tests for GET /config/list endpoint."""

    def test_list_configs(self, reset_app_state, temp_configs_dir):
        """Test listing available configurations."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/config/list")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "basic_agent" in names
        assert "advanced_agent" in names

    def test_list_configs_empty_dir(self, reset_app_state):
        """Test listing configs when directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["CONFIGS_DIR"] = tmpdir
            app = create_app()
            client = TestClient(app)

            response = client.get("/config/list")

            assert response.status_code == 200
            data = response.json()
            assert data == []


class TestLoadConfig:
    """Tests for PUT /config endpoint."""

    def test_load_config_success(self, reset_app_state, temp_configs_dir):
        """Test successfully loading a configuration."""
        app = create_app()
        client = TestClient(app)

        response = client.put("/config", json={"config_name": "basic_agent"})

        assert response.status_code == 200
        data = response.json()
        assert "loaded successfully" in data["message"]
        assert data["greeting"] == "Hello from basic!"

    def test_load_config_with_extension(self, reset_app_state, temp_configs_dir):
        """Test loading config with .yaml extension."""
        app = create_app()
        client = TestClient(app)

        response = client.put("/config", json={"config_name": "basic_agent.yaml"})

        assert response.status_code == 200

    def test_load_config_not_found(self, reset_app_state, temp_configs_dir):
        """Test loading non-existent configuration."""
        app = create_app()
        client = TestClient(app)

        response = client.put("/config", json={"config_name": "nonexistent"})

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_load_config_with_active_conversations(
        self, basic_config, reset_app_state, temp_configs_dir
    ):
        """Test that loading config fails when conversations are active."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        # Start a conversation
        client.post("/conversations")

        # Try to change config
        response = client.put("/config", json={"config_name": "advanced_agent"})

        assert response.status_code == 409
        assert "active" in response.json()["detail"].lower()

    def test_load_config_after_conversation_deleted(
        self, basic_config, reset_app_state, temp_configs_dir
    ):
        """Test loading config works after deleting active conversations."""
        app = create_app(config=basic_config)
        client = TestClient(app)

        # Start and then delete a conversation
        start_response = client.post("/conversations")
        session_id = start_response.json()["session_id"]
        client.delete(f"/conversations/{session_id}")

        # Now config change should work
        response = client.put("/config", json={"config_name": "advanced_agent"})

        assert response.status_code == 200
        assert "Hello from advanced!" in response.json()["greeting"]


class TestConfigSwitch:
    """Integration tests for configuration switching."""

    def test_switch_config_changes_agent_behavior(self, reset_app_state, temp_configs_dir):
        """Test that switching config actually changes agent behavior."""
        app = create_app()
        client = TestClient(app)

        # Load basic config
        client.put("/config", json={"config_name": "basic_agent"})

        current = client.get("/config/current").json()
        assert current["greeting"] == "Hello from basic!"
        assert len(current["fields"]) == 1

        # Switch to advanced config
        client.put("/config", json={"config_name": "advanced_agent"})

        current = client.get("/config/current").json()
        assert current["greeting"] == "Hello from advanced!"
        assert len(current["fields"]) == 2
