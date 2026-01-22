"""Konko AI Conversational Agent - Configuration Package."""

from .loader import ConfigurationError, load_config_from_dict, load_config_from_yaml
from .schemas import AgentConfig, AgentPersonality, EscalationPolicy, FieldConfig, Formality, Tone

__version__ = "0.1.0"

__all__ = [
    "AgentConfig",
    "AgentPersonality",
    "ConfigurationError",
    "EscalationPolicy",
    "FieldConfig",
    "Formality",
    "Tone",
    "load_config_from_dict",
    "load_config_from_yaml",
]
