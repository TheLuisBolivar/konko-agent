# Konko AI Conversational Agent

A production-ready, configurable conversational agent built with LangChain, LangGraph, and Redis.

## Overview

This project implements a conversational agent with **dual interfaces**:
- **FastAPI REST API + WebSockets** for production use
- **Interactive CLI** for development and testing

The agent:
- Collects user information through natural conversation
- Handles corrections and interruptions gracefully
- Escalates to human agents when appropriate
- Supports flexible configuration via YAML

## Features

### Core Features
- ✅ **FastAPI REST API** with Swagger documentation
- ✅ **WebSocket support** for real-time conversations
- ✅ **Interactive CLI** for quick testing
- ✅ Sequential field collection with validation
- ✅ Natural language understanding via LLM
- ✅ Correction handling ("No, my email is...")
- ✅ Multiple escalation policies (keyword, timeout)
- ✅ Configurable personality (tone, style, formality, emojis)
- ✅ Docker + Docker Compose ready
- ✅ Comprehensive test suite

## Requirements

- Python 3.11+
- OpenAI API key
- Redis (optional, for persistence)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd konko-agent
```

2. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Set up environment variables:
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
# Required: OPENAI_API_KEY
# Optional: LANGCHAIN_API_KEY for LangSmith tracing
```

## Quick Start

### Option 1: FastAPI Server (Recommended)

1. Start the API server:
```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

2. Access the API:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

3. Start a conversation via REST:
```bash
# Start new conversation
curl -X POST http://localhost:8000/api/v1/conversations

# Send a message
curl -X POST http://localhost:8000/api/v1/conversations/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "My name is John Doe"}'
```

4. Or use WebSocket for real-time chat:
```javascript
// Connect to WebSocket
ws://localhost:8000/api/v1/ws/{session_id}
```

### Option 2: CLI (For testing)

```bash
python cli.py examples/basic_agent.yaml
```

### Option 3: Docker Compose

```bash
docker-compose up --build
# API available at http://localhost:8000
```

## Development

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=packages --cov-report=html

# Run specific test types
pytest tests/unit/ -v
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
black packages/ tests/

# Sort imports
isort packages/ tests/

# Lint
ruff check packages/ tests/

# Type check
mypy packages/
```

## Project Structure

```
konko-agent/
├── packages/
│   ├── agent-core/          # Core agent logic
│   ├── agent-runtime/       # Orchestration & infrastructure
│   └── agent-config/        # Configuration management
├── tests/                   # Test suite
├── examples/                # Sample configurations
├── docs/                    # Documentation
└── cli.py                   # Command-line interface
```

## Architecture

The project follows a multi-package architecture with clear separation of concerns:

- **agent-core**: Agent behavior and conversation logic
- **agent-runtime**: Infrastructure (state management, LLM integration, messaging)
- **agent-config**: Configuration loading and validation

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for detailed architecture decisions.

## Configuration

Agents are configured via YAML files. See `examples/` for sample configurations.

Basic configuration structure:
```yaml
personality:
  tone: friendly
  style: conversational
  formality: neutral
  emoji_usage: true

greeting: "Hi there! How can I help you today?"

fields:
  - name: name
    field_type: text
    required: true
    prompt_hint: "What's your name?"

escalation_policies:
  - enabled: true
    reason: "User requested human agent"
    policy_type: keyword
    config:
      keywords: ["human", "agent", "help"]
```

## License

MIT

## Contributing

See [DECISIONS.md](DECISIONS.md) for architecture decisions and development guidelines.
