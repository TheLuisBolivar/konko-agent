#!/usr/bin/env python3
"""Configuration management tools for Konko AI Agent.

Usage:
    python scripts/config_tools.py list          # List available configs
    python scripts/config_tools.py validate      # Validate all configs
    python scripts/config_tools.py validate FILE # Validate specific config
    python scripts/config_tools.py show FILE     # Show config details
"""

import sys
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_config import ConfigurationError, load_config_from_yaml  # noqa: E402

CONFIGS_DIR = Path("configs")

# Colors
GREEN = "\033[0;32m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color


def _print_config_info(config_file: Path) -> None:
    """Print basic info for a configuration file."""
    try:
        config = load_config_from_yaml(str(config_file))
        print(f"    Greeting: {config.greeting[:50]}...")
        print(f"    Fields: {len(config.fields)}")
        print(f"    LLM: {config.llm.provider.value}/{config.llm.model_name}")
    except Exception as e:
        print(f"    {RED}Error loading: {e}{NC}")


def list_configs() -> None:
    """List all available configuration files."""
    print(f"{BLUE}Available configurations:{NC}\n")

    if not CONFIGS_DIR.exists():
        print(f"{RED}  No configs directory found at {CONFIGS_DIR}{NC}")
        return

    configs = list(CONFIGS_DIR.glob("*.yaml")) + list(CONFIGS_DIR.glob("*.yml"))

    if not configs:
        print(f"{YELLOW}  No configuration files found in {CONFIGS_DIR}/{NC}")
        return

    for config_file in sorted(configs):
        print(f"  {GREEN}•{NC} {config_file.stem}")
        print(f"    Path: {config_file}")
        _print_config_info(config_file)
        print()


def _validate_single_config(config_file: Path) -> bool:
    """Validate a single configuration file."""
    print(f"  Checking {config_file.name}...", end=" ")

    if not config_file.exists():
        print(f"{RED}✗ File not found{NC}")
        return False

    try:
        config = load_config_from_yaml(str(config_file))
        errors = []

        if not config.greeting:
            errors.append("Missing greeting")
        if not config.fields:
            errors.append("No fields defined")

        required_fields = [f for f in config.fields if f.required]
        if not required_fields:
            errors.append("No required fields (at least one recommended)")

        if errors:
            print(f"{YELLOW}⚠ Warnings: {', '.join(errors)}{NC}")
        else:
            print(f"{GREEN}✓ Valid{NC}")
        return True

    except ConfigurationError as e:
        print(f"{RED}✗ Invalid: {e}{NC}")
        return False
    except Exception as e:
        print(f"{RED}✗ Error: {e}{NC}")
        return False


def validate_config(config_path: str | None = None) -> bool:
    """Validate configuration file(s)."""
    if config_path:
        configs = [Path(config_path)]
    else:
        configs = list(CONFIGS_DIR.glob("*.yaml")) + list(CONFIGS_DIR.glob("*.yml"))

    if not configs:
        print(f"{RED}No configuration files found{NC}")
        return False

    print(f"{BLUE}Validating configurations...{NC}\n")

    all_valid = all(_validate_single_config(cf) for cf in sorted(configs))

    print()
    if all_valid:
        print(f"{GREEN}All configurations are valid!{NC}")
    else:
        print(f"{RED}Some configurations have errors.{NC}")

    return all_valid


def _resolve_config_path(config_path: str) -> Path:
    """Resolve configuration path from name or full path."""
    path = Path(config_path)

    if path.exists():
        return path

    if not path.suffix:
        yaml_path = CONFIGS_DIR / f"{config_path}.yaml"
        if yaml_path.exists():
            return yaml_path
        yml_path = CONFIGS_DIR / f"{config_path}.yml"
        if yml_path.exists():
            return yml_path

    return path


def _print_config_details(config) -> None:  # noqa: C901
    """Print detailed configuration information."""
    print(f"{GREEN}Greeting:{NC}")
    print(f"  {config.greeting}\n")

    print(f"{GREEN}Personality:{NC}")
    print(f"  Tone: {config.personality.tone.value}")
    print(f"  Style: {config.personality.style}")
    print(f"  Formality: {config.personality.formality.value}")
    print(f"  Emoji usage: {config.personality.emoji_usage}")
    if config.personality.emoji_usage and config.personality.emoji_list:
        print(f"  Emojis: {', '.join(config.personality.emoji_list[:5])}")
    print()

    print(f"{GREEN}LLM Configuration:{NC}")
    print(f"  Provider: {config.llm.provider.value}")
    print(f"  Model: {config.llm.model_name}")
    print(f"  Temperature: {config.llm.temperature}")
    if config.llm.max_tokens:
        print(f"  Max tokens: {config.llm.max_tokens}")
    print()

    print(f"{GREEN}Fields to collect ({len(config.fields)}):{NC}")
    for i, field in enumerate(config.fields, 1):
        required = f"{RED}*{NC}" if field.required else " "
        print(f"  {i}. {required} {field.name} ({field.field_type})")
        if field.prompt_hint:
            print(f"       Hint: {field.prompt_hint}")
        if field.validation_pattern:
            print(f"       Pattern: {field.validation_pattern}")
    print()

    if config.escalation_policies:
        print(f"{GREEN}Escalation Policies ({len(config.escalation_policies)}):{NC}")
        for policy in config.escalation_policies:
            status = f"{GREEN}enabled{NC}" if policy.enabled else f"{YELLOW}disabled{NC}"
            print(f"  • {policy.policy_type} ({status})")
            print(f"      Reason: {policy.reason}")
    else:
        print(f"{YELLOW}No escalation policies defined{NC}")


def show_config(config_path: str) -> None:
    """Display detailed configuration information."""
    path = _resolve_config_path(config_path)

    if not path.exists():
        print(f"{RED}Configuration file not found: {config_path}{NC}")
        sys.exit(1)

    print(f"{BLUE}Configuration: {path.name}{NC}")
    print(f"{'=' * 50}\n")

    try:
        config = load_config_from_yaml(str(path))
        _print_config_details(config)
    except Exception as e:
        print(f"{RED}Error loading configuration: {e}{NC}")
        sys.exit(1)


def main() -> None:
    """Execute the configuration tool command."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "list":
        list_configs()
    elif command == "validate":
        config_path = sys.argv[2] if len(sys.argv) > 2 else None
        success = validate_config(config_path)
        sys.exit(0 if success else 1)
    elif command == "show":
        if len(sys.argv) < 3:
            print(f"{RED}Usage: config_tools.py show <config_name>{NC}")
            sys.exit(1)
        show_config(sys.argv[2])
    else:
        print(f"{RED}Unknown command: {command}{NC}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
