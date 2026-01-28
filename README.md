# Konko AI Conversational Agent

A configurable conversational agent built with LangChain, LangGraph, and FastAPI for collecting user information through natural dialogue.

[![CI](https://github.com/TheLuisBolivar/konko-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/TheLuisBolivar/konko-agent/actions/workflows/ci.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=coverage)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## ⚡ Quick Local Deploy

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key
- (Optional) LangSmith API Key for tracing

### 1. Setup

```bash
# Clone and enter project
git clone https://github.com/TheLuisBolivar/konko-agent.git
cd konko-agent

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys:
#   OPENAI_API_KEY=sk-proj-...
#   LANGCHAIN_TRACING_V2=true        # Enable LangSmith
#   LANGCHAIN_API_KEY=lsv2_pt_...    # Your LangSmith key
```

### 2. Start Everything

```bash
make up
```

This starts: **Agent API** + **Prometheus** + **Grafana**

### 3. Quick Test

```bash
# Run a test conversation
make test-flow

# Check metrics
make metrics

# Check health of all services
make health
```

### 4. Platform URLs

| Platform | URL | Credentials |
|----------|-----|-------------|
| **API Docs (Swagger)** | http://localhost:8000/docs | - |
| **Metrics Endpoint** | http://localhost:8000/metrics/ | - |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana Dashboard** | http://localhost:3000 | admin / admin |
| **LangSmith Traces** | https://smith.langchain.com | Your account |

### 5. Stop

```bash
make down
```

---

## 🚀 Features

- ✅ **LangGraph State Machine** for conversational flow control
- ✅ **YAML-based configuration** with Pydantic validation
- ✅ **State management** thread-safe with Redis support
- ✅ **Multiple escalation policies** (keyword, timeout, sentiment, LLM intent)
- ✅ **Correction detection** ("No, my email is...")
- ✅ **Off-topic detection** and automatic redirect
- ✅ **Dual interface**: REST API + WebSocket and CLI
- ✅ **Type-safe** with mypy strict mode (100% type coverage)
- ✅ **High test coverage** (264 tests passing)
- ✅ **Code quality guaranteed** with pre-commit hooks
- ✅ **Automatic security analysis** with Bandit
- ✅ **Controlled complexity** (<10 per function)

## 🔄 Conversation Flow Architecture

The agent uses a **LangGraph-based state machine** to control the conversation flow:

```
START → check_escalation
           │
    ┌──────┴──────┐
    ↓             ↓
escalate    check_correction
    ↓             │
   END     ┌──────┴──────┐
           ↓             ↓
    extract_field   check_off_topic
           │             │
           ↓      ┌──────┴──────┐
        validate  ↓             ↓
           │   prompt_next   complete
    ┌──────┴──────┐   │         ↓
    ↓             ↓   ↓        END
prompt_next   complete
    ↓             ↓
   END           END
```

### Graph Nodes

| Node | Description |
|------|-------------|
| `check_escalation` | Evaluates escalation policies (keyword, timeout, sentiment, etc.) |
| `check_correction` | Detects user corrections ("No, my email is...") |
| `check_off_topic` | Identifies off-topic responses |
| `extract_field` | Extracts field values from user message |
| `validate` | Validates extracted value against field type |
| `prompt_next` | Generates prompt for next field or re-asks |
| `escalate` | Handles escalation to human agent |
| `complete` | Generates completion message when all fields are collected |

For more details, see [docs/CONVERSATION_FLOW.md](docs/CONVERSATION_FLOW.md)

## 📦 Installation

### Requirements

- Python 3.10+
- pip
- git

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/TheLuisBolivar/konko-agent.git
cd konko-agent

# Complete setup (venv, deps, git hooks)
make setup

# Activate virtual environment
source .venv/bin/activate

# Verify installation
make verify
```

The `make setup` command automatically installs:
- Python virtual environment
- All dependencies (production + development)
- Pre-commit git hooks (formatting, linting, tests, security)

### Docker

```bash
# Option 1: Use DockerHub image
docker pull theluisbolivar/konko-agent:latest
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY theluisbolivar/konko-agent:latest

# Option 2: Local build
docker build -t konko-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY konko-agent

# Option 3: Docker Compose
docker-compose up konko-agent

# Development with hot reload
docker-compose --profile dev up konko-agent-dev
```

## 🏃 Quick Start

### 1. Test basic configuration

```bash
# Load and validate configuration
python -c "
from agent_config import load_config_from_yaml
config = load_config_from_yaml('configs/basic_agent.yaml')
print(f'✓ Config loaded: {len(config.fields)} fields')
print(f'  Personality: {config.personality.tone}')
print(f'  Greeting: {config.greeting}')
"
```

**Expected output:**
```
✓ Config loaded: 3 fields
  Personality: Tone.PROFESSIONAL
  Greeting: Hello! I'm here to help collect some information from you today.
```

### 2. Test state management

```bash
# Create and manage conversation
python -c "
from agent_runtime import ConversationState, get_default_store, MessageRole

store = get_default_store()
state = ConversationState()
store.create(state)

state.add_message(MessageRole.AGENT, 'What is your name?')
state.add_message(MessageRole.USER, 'Luis')
state.update_field_value('name', 'Luis', True)

print(f'✓ Session created: {state.session_id}')
print(f'  Messages: {len(state.messages)}')
print(f'  Collected data: {state.get_collected_data()}')

store.clear()
"
```

**Expected output:**
```
✓ Session created: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Messages: 2
  Collected data: {'name': 'Luis'}
```

### 3. Run tests

```bash
# Unit tests
make test

# Tests with coverage report
make test-cov

# View HTML coverage report
open htmlcov/index.html
```

## 🛠️ Development

### Available Commands

```bash
make help              # Show all available commands
make verify            # Verify setup and dependencies
make test              # Run unit tests
make test-cov          # Tests with coverage report (HTML + terminal)
make format            # Format code (black + isort)
make lint              # Lint code (ruff + mypy)
make quality           # ⭐ Run ALL quality checks
make quality-check     # Check quality without auto-fix (for CI)
make security          # Run security analysis
make hooks-run         # Run pre-commit hooks manually
make hooks-install     # Reinstall git hooks
make clean             # Clean generated files
make status            # Show git status and recent commits
```

### Automatic Pre-commit Hooks

Hooks run **automatically** on commit/push:

**On `git commit`:**
- ✅ Automatic formatting (Black, isort)
- ✅ Linting (Ruff, Flake8 with complexity)
- ✅ Type checking (mypy strict)
- ✅ Security scan (Bandit)
- ✅ Docstring validation (pydocstyle)
- ✅ Quick unit tests

**On `git push`:**
- ✅ All of the above
- ✅ Full tests with coverage (minimum 80%)

See more details in [docs/PRE_COMMIT_HOOKS.md](docs/PRE_COMMIT_HOOKS.md)

### Development Workflow

```bash
# 1. Make changes
vim packages/agent_config/schemas.py

# 2. Commit (hooks run automatically)
git add .
git commit -m "feat: add new feature"
# ⬆️ Hooks verify quality automatically

# 3. If something fails, fix and re-commit
# Some hooks auto-fix (black, isort, ruff)
git add .
git commit -m "feat: add new feature"

# 4. Push (runs full tests)
git push origin feature/my-feature
```

## 📁 Project Structure

```
konko-agent/
├── packages/                    # Project source code
│   ├── agent_config/           # ✅ Configuration and validation
│   │   ├── __init__.py
│   │   ├── schemas.py          # Pydantic models
│   │   └── loader.py           # YAML loader
│   ├── agent_runtime/          # ✅ State management
│   │   ├── __init__.py
│   │   ├── state.py            # State models
│   │   └── store.py            # Thread-safe store
│   └── agent_core/             # ✅ Agent logic
│       ├── __init__.py
│       ├── agent.py            # Main agent
│       ├── llm_provider.py     # LLM provider
│       ├── metrics.py          # Prometheus metrics
│       ├── escalation/         # Escalation engine
│       │   ├── engine.py
│       │   ├── handlers/       # Policy handlers
│       │   └── ...
│       └── graph/              # ✅ LangGraph State Machine
│           ├── __init__.py
│           ├── state.py        # GraphState TypedDict
│           ├── nodes.py        # 8 node functions
│           ├── edges.py        # Routing functions
│           └── builder.py      # Graph builder
│
├── configs/                     # Example configurations
│   ├── basic_agent.yaml        # Basic config (3 fields)
│   ├── advanced_agent.yaml     # Advanced config (7 fields)
│   ├── prometheus.yml          # Prometheus scrape config
│   └── grafana/                # Grafana provisioning
│
├── tests/                       # Test suite (264 tests)
│   └── unit/
│       ├── test_agent.py
│       ├── test_config_*.py
│       ├── test_state.py
│       ├── test_store.py
│       ├── test_escalation_*.py
│       ├── test_graph_nodes.py      # Node tests
│       ├── test_graph_edges.py      # Routing tests
│       └── test_graph_integration.py # Flow tests
│
├── docs/                        # Documentation
│   ├── CONVERSATION_FLOW.md    # Conversation flow architecture
│   ├── PRE_COMMIT_HOOKS.md     # Git hooks guide
│   └── CODE_QUALITY_TOOLS.md   # Quality tools
│
├── scripts/                     # Utility scripts
│   ├── verify_setup.py         # Setup verification
│   └── test_progress.sh        # Progress check
│
├── .pre-commit-config.yaml     # Hooks configuration
├── pyproject.toml              # Project configuration
├── Makefile                    # Development commands
└── README.md                   # This file
```

## 📊 Quality Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Tests** | 264/264 passing | ✅ 100% |
| **Coverage** | >95% | ✅ Excellent |
| **Type Coverage** | 100% (mypy strict) | ✅ Perfect |
| **Complexity** | <10 per function | ✅ Low |
| **Security** | 0 vulnerabilities | ✅ Secure |
| **Linting** | 0 errors | ✅ Clean |

### Detailed Coverage

```
Name                                 Stmts   Miss   Cover
-----------------------------------------------------------
packages/agent_config/__init__.py        4      0 100.00%
packages/agent_config/loader.py         33      2  93.94%
packages/agent_config/schemas.py        89      0 100.00%
packages/agent_runtime/__init__.py       4      0 100.00%
packages/agent_runtime/state.py         80      0 100.00%
packages/agent_runtime/store.py         72      0 100.00%
-----------------------------------------------------------
TOTAL                                  283      3  98.94%
```

## 🔧 Configuration

### Basic Example

`configs/basic_agent.yaml`:

```yaml
personality:
  tone: professional          # friendly, professional, casual, empathetic
  style: concise
  formality: neutral          # formal, neutral, informal
  emoji_usage: false

greeting: "Hello! I'm here to help collect some information."

fields:
  - name: full_name
    field_type: text
    required: true
    prompt_hint: "What's your full name?"

  - name: email
    field_type: email
    required: true
    validation_pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    prompt_hint: "What's your email address?"

  - name: phone_number
    field_type: phone
    required: false
    prompt_hint: "What's your phone number? (Optional)"

escalation_policies:
  - enabled: true
    reason: "User requested human assistance"
    policy_type: keyword
    config:
      keywords: ["human", "agent", "help", "representative"]

  - enabled: true
    reason: "Conversation took too long"
    policy_type: timeout
    config:
      max_duration_seconds: 600  # 10 minutes
```

### Advanced Example

See `configs/advanced_agent.yaml` for an example with:
- 7 fields of different types (text, email, phone, url, number, date)
- 5 escalation policies (keyword, timeout, sentiment, llm_intent, completion)
- Friendly personality with emojis enabled

## 🌐 Testing the API

### Start the Server

```bash
# Activate environment and set API key
source .venv/bin/activate
export OPENAI_API_KEY="sk-your-api-key"

# Start server (port 8000)
python main.py
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations` | Start new conversation |
| `POST` | `/conversations/{id}/messages` | Send message |
| `GET` | `/conversations/{id}` | Get conversation state |
| `DELETE` | `/conversations/{id}` | Delete conversation |
| `WS` | `/ws` | WebSocket for real-time |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI (interactive docs) |
| `GET` | `/metrics/` | Prometheus metrics |

### Test with curl

```bash
# 1. Start conversation
curl -X POST http://localhost:8000/conversations | jq

# 2. Send message (replace SESSION_ID)
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "My name is Luis"}' | jq

# 3. Test correction
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "No, my name is Luis Bolivar"}' | jq

# 4. Test off-topic (agent redirects)
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "What time is it?"}' | jq

# 5. Get conversation state
curl -X GET "http://localhost:8000/conversations/SESSION_ID" | jq
```

### Test with WebSocket

```bash
# Requires wscat: npm install -g wscat
wscat -c ws://localhost:8000/ws

# Once connected, send messages:
> {"type": "message", "content": "My name is Luis"}
> {"type": "message", "content": "luis@example.com"}
```

### Swagger UI

Open `http://localhost:8000/docs` in your browser to test the API interactively.

## 🧪 Testing

### Run Tests

```bash
# All tests with verbose output
pytest tests/unit/ -v

# With detailed coverage
pytest tests/unit/ --cov=packages --cov-report=term-missing

# Specific tests only
pytest tests/unit/test_config_schemas.py -v

# Run a specific test
pytest tests/unit/test_state.py::TestConversationState::test_add_message -v

# With warnings disabled
pytest tests/unit/ -v --disable-warnings
```

### Writing Tests

Tests use `pytest` and follow this structure:

```python
"""Tests for my module."""

import pytest
from agent_config import AgentConfig, FieldConfig

class TestMyFeature:
    """Tests for MyFeature."""

    def test_basic_functionality(self):
        """Test basic functionality works."""
        config = AgentConfig(fields=[FieldConfig(name="test")])
        assert len(config.fields) == 1

    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError) as exc_info:
            FieldConfig(name="")
        assert "cannot be empty" in str(exc_info.value)
```

## 🔒 Security

### Automatic Analysis

- **Bandit**: Scans code for vulnerabilities
- **Pre-commit**: Detects private keys before commit
- **Dependabot** (coming soon): Automatic dependency updates
- **Safety** (recommended): CVE scanning for dependencies

### Run Manual Scan

```bash
# Full security analysis
make security

# Bandit only
source .venv/bin/activate
bandit -r packages/ -c pyproject.toml

# Check dependencies (requires installing safety)
pip install safety
safety check
```

### Best Practices

- ✅ **Don't commit** `.env` files (in `.gitignore`)
- ✅ **Don't hardcode** credentials in code
- ✅ **Use environment variables** for secrets
- ✅ **Review dependencies** regularly
- ✅ **Keep Python updated** (3.10+)

## 📚 Documentation

- **[Conversation Flow](docs/CONVERSATION_FLOW.md)** - Conversation flow architecture (LangGraph)
- **[Pre-commit Hooks](docs/PRE_COMMIT_HOOKS.md)** - Complete git hooks guide
- **[Code Quality Tools](docs/CODE_QUALITY_TOOLS.md)** - Quality tools and recommendations
- **[Implementation Plan](.epsilon/)** - Detailed implementation plan

## 🤝 Contributing

### Pull Request Requirements

For a PR to be accepted it must meet:

- ✅ **All tests passing** (264/264)
- ✅ **Coverage >80%** (currently >95%)
- ✅ **Code formatted** (black + isort)
- ✅ **No linting errors** (ruff + flake8)
- ✅ **Complete type hints** (mypy strict)
- ✅ **Docstrings on public code** (Google style)
- ✅ **No security** vulnerabilities
- ✅ **Approval from @TheLuisBolivar** (CODEOWNERS)

### Contribution Process

1. **Fork** the project
2. **Create** your feature branch (`git checkout -b feature/amazing-feature`)
3. **Develop** with hooks enabled (installed automatically)
4. **Commit** your changes (hooks verify quality)
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
5. **Push** to the branch (runs full tests)
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Open** a Pull Request with detailed description

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new feature
fix: resolve bug in state management
docs: update README with examples
style: format code with black
refactor: restructure configuration loader
test: add tests for escalation policies
chore: update dependencies
```

## 🐛 Troubleshooting

### "Pre-commit hooks too slow"

The first run is slow (downloads tools). Subsequent runs are fast.

```bash
# For urgent commits (NOT RECOMMENDED)
git commit --no-verify -m "message"
```

### "Tests fail locally but passed before"

```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -e ".[dev]"

# Clean cache
make clean

# Re-run tests
make test
```

### "Low coverage after adding code"

```bash
# See which lines are missing
pytest --cov=packages --cov-report=term-missing

# Add tests for missing lines
```

### "Mypy reports type errors"

```bash
# Install missing types
pip install types-PyYAML types-redis

# Check types
mypy packages/
```

## 🐳 Docker Hub Publishing (CI/CD)

The CI pipeline automatically builds and publishes Docker images to Docker Hub on pushes to `main`.

### Docker Hub Image

```bash
docker pull theluisbolivar/konko-agent:latest
```

👉 **[Docker Hub Repository](https://hub.docker.com/r/theluisbolivar/konko-agent)**

### Configure Docker Hub (For Forks)

To enable automatic Docker image publishing in your fork:

1. **Create Docker Hub Access Token**
   - Go to [Docker Hub](https://hub.docker.com) → Account Settings → Security
   - Click **New Access Token**
   - Name: `github-actions`
   - Permissions: **Read & Write**
   - Copy the generated token

2. **Add GitHub Secrets**
   - Go to your GitHub repo → Settings → Secrets and variables → Actions
   - Add these secrets:
     | Secret | Value |
     |--------|-------|
     | `DOCKERHUB_USERNAME` | Your Docker Hub username |
     | `DOCKERHUB_TOKEN` | The access token from step 1 |

3. **Push to main**
   - The CI workflow will automatically build and push the image
   - Image tags: `latest` and commit SHA

---

## 📊 Static Code Analysis (SonarCloud)

This project uses **SonarCloud** for free static code analysis.

### View Results

Analysis results are publicly available at:

👉 **[SonarCloud Dashboard](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)**

### Analyzed Metrics

| Metric | Description |
|--------|-------------|
| **Quality Gate** | Overall code quality status |
| **Coverage** | Test coverage (>95%) |
| **Maintainability** | Complexity and technical debt |
| **Reliability** | Bugs and reliability issues |
| **Security** | Vulnerabilities and hotspots |
| **Duplications** | Duplicated code |

### Configure SonarCloud (For Forks)

1. Import the project at [sonarcloud.io](https://sonarcloud.io)
2. Add the `SONAR_TOKEN` secret in GitHub Actions
3. Analysis will run automatically on each PR

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/TheLuisBolivar/konko-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/TheLuisBolivar/konko-agent/discussions)
- **Email**: luis@konko.ai
- **Security**: security@konko.ai

## 📄 License

This project is private and confidential.

## 👥 Team

- [@TheLuisBolivar](https://github.com/TheLuisBolivar) - Lead Developer & Code Owner

## 🙏 Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) - LLM Framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - State machines for LLMs
- [FastAPI](https://github.com/tiangolo/fastapi) - Modern web framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [pre-commit](https://pre-commit.com/) - Git hooks framework

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
