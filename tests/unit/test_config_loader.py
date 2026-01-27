"""Tests for configuration loader."""

import pytest
from agent_config import ConfigurationError, load_config_from_dict, load_config_from_yaml
from agent_config.schemas import AgentConfig, Tone


class TestLoadConfigFromYaml:
    """Tests for load_config_from_yaml function."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid YAML configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
personality:
  tone: friendly
  style: concise

greeting: "Hello!"

fields:
  - name: email
    field_type: email
    required: true
"""
        )

        config = load_config_from_yaml(config_file)

        assert isinstance(config, AgentConfig)
        assert config.personality.tone == Tone.FRIENDLY
        assert config.greeting == "Hello!"
        assert len(config.fields) == 1
        assert config.fields[0].name == "email"

    def test_load_config_with_escalation_policies(self, tmp_path):
        """Test loading config with escalation policies."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
greeting: "Hi there!"

fields:
  - name: name
    field_type: text

escalation_policies:
  - enabled: true
    reason: "User requested help"
    policy_type: keyword
    config:
      keywords:
        - "help"
        - "human"
"""
        )

        config = load_config_from_yaml(config_file)

        assert len(config.escalation_policies) == 1
        assert config.escalation_policies[0].policy_type == "keyword"
        assert config.escalation_policies[0].enabled is True

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config_from_yaml("/nonexistent/path/config.yaml")

        assert "not found" in str(exc_info.value)

    def test_invalid_yaml_syntax(self, tmp_path):
        """Test that ConfigurationError is raised for invalid YAML."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(
            """
greeting: "Hello
fields:
  - name: [invalid syntax here
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(config_file)

        assert "parse YAML" in str(exc_info.value)

    def test_empty_config_file(self, tmp_path):
        """Test that ConfigurationError is raised for empty file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(config_file)

        assert "empty" in str(exc_info.value).lower()

    def test_non_dict_config(self, tmp_path):
        """Test that ConfigurationError is raised for non-dict YAML."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2\n")

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(config_file)

        assert "must be" in str(exc_info.value)

    def test_validation_error(self, tmp_path):
        """Test that ConfigurationError is raised for invalid config data."""
        config_file = tmp_path / "invalid_config.yaml"
        config_file.write_text(
            """
greeting: ""  # Empty greeting - should fail validation
fields:
  - name: email
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(config_file)

        assert "validation failed" in str(exc_info.value).lower()

    def test_missing_required_field(self, tmp_path):
        """Test that ConfigurationError is raised when required field is missing."""
        config_file = tmp_path / "missing_field.yaml"
        config_file.write_text(
            """
greeting: "Hello!"
# Missing 'fields' which is required
"""
        )

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(config_file)

        assert "validation failed" in str(exc_info.value).lower()

    def test_config_directory_path(self, tmp_path):
        """Test that ConfigurationError is raised for directory path."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_yaml(tmp_path)

        assert "not a file" in str(exc_info.value)


class TestLoadConfigFromDict:
    """Tests for load_config_from_dict function."""

    def test_load_valid_dict(self):
        """Test loading a valid configuration dictionary."""
        config_dict = {
            "personality": {"tone": "professional", "style": "concise"},
            "greeting": "Hello!",
            "fields": [{"name": "email", "field_type": "email"}],
        }

        config = load_config_from_dict(config_dict)

        assert isinstance(config, AgentConfig)
        assert config.personality.tone == Tone.PROFESSIONAL
        assert config.greeting == "Hello!"
        assert len(config.fields) == 1

    def test_load_minimal_dict(self):
        """Test loading minimal valid configuration."""
        config_dict = {"fields": [{"name": "name"}]}  # Only required field

        config = load_config_from_dict(config_dict)

        assert len(config.fields) == 1
        assert config.fields[0].name == "name"
        assert config.greeting  # Should have default value

    def test_validation_error(self):
        """Test that ConfigurationError is raised for invalid dict."""
        config_dict = {
            "greeting": "",  # Empty greeting - should fail
            "fields": [{"name": "email"}],
        }

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_dict(config_dict)

        assert "validation failed" in str(exc_info.value).lower()

    def test_missing_required_field(self):
        """Test that ConfigurationError is raised when required field is missing."""
        config_dict = {"greeting": "Hello!"}  # Missing 'fields'

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_dict(config_dict)

        assert "validation failed" in str(exc_info.value).lower()

    def test_invalid_field_type(self):
        """Test that ConfigurationError is raised for invalid field type."""
        config_dict = {"fields": [{"name": "custom", "field_type": "invalid_type"}]}

        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_dict(config_dict)

        assert "validation failed" in str(exc_info.value).lower()


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_error_message(self):
        """Test that ConfigurationError can be raised with custom message."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_error_inheritance(self):
        """Test that ConfigurationError inherits from Exception."""
        assert issubclass(ConfigurationError, Exception)
