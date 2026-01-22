"""Configuration loader for Konko AI Agent.

This module provides utilities to load and validate agent configuration from YAML files.
"""

from pathlib import Path
from typing import Any, Dict, Union

import yaml
from pydantic import ValidationError

from .schemas import AgentConfig


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


def load_config_from_yaml(config_path: Union[str, Path]) -> AgentConfig:
    """Load and validate agent configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Validated AgentConfig instance

    Raises:
        ConfigurationError: If the file cannot be read or validation fails
        FileNotFoundError: If the configuration file doesn't exist
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    if not path.is_file():
        raise ConfigurationError(f"Configuration path is not a file: {config_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Failed to parse YAML file: {e}") from e
    except OSError as e:
        raise ConfigurationError(f"Failed to read configuration file: {e}") from e

    if config_data is None:
        raise ConfigurationError("Configuration file is empty")

    if not isinstance(config_data, dict):
        raise ConfigurationError("Configuration must be a YAML object (dict)")

    try:
        return AgentConfig(**config_data)
    except ValidationError as e:
        raise ConfigurationError(f"Configuration validation failed: {e}") from e


def load_config_from_dict(config_dict: Dict[str, Any]) -> AgentConfig:
    """Load and validate agent configuration from a dictionary.

    Args:
        config_dict: Configuration dictionary

    Returns:
        Validated AgentConfig instance

    Raises:
        ConfigurationError: If validation fails
    """
    try:
        return AgentConfig(**config_dict)
    except ValidationError as e:
        raise ConfigurationError(f"Configuration validation failed: {e}") from e
