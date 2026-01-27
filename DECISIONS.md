# Architecture Decisions

This document describes the key architectural decisions, tradeoffs, and design rationale for the Konko AI Conversational Agent.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Design Decisions](#key-design-decisions)
- [Tradeoffs](#tradeoffs)
- [What I Would Do With One Additional Day](#what-i-would-do-with-one-additional-day)
- [AI Coding Tools Usage](#ai-coding-tools-usage)

---

## Architecture Overview

The system follows a **modular monorepo** structure with clear separation of concerns:

```
packages/
├── agent_config/     # Configuration validation (Pydantic models)
├── agent_core/       # Agent logic and LangGraph state machine
│   ├── graph/        # State machine (nodes, edges, state)
│   └── escalation/   # Escalation engine with pluggable handlers
├── agent_runtime/    # State management and orchestration
└── agent_api/        # FastAPI REST + WebSocket interface
```

### Why This Structure?

1. **Package Independence**: Each package can be versioned, tested, and deployed independently
2. **Clear Boundaries**: Config validation is separate from agent logic, which is separate from API
3. **Testability**: Each layer can be tested in isolation with mocked dependencies
4. **Extensibility**: New escalation handlers, field types, or API endpoints can be added without touching core logic

---

## Key Design Decisions

### 1. LangGraph State Machine for Conversation Flow

**Decision**: Use LangGraph to implement a state machine for conversation control.

**Rationale**:
- **Explicit Flow Control**: The conversation flow is visualized as a graph, making it easy to understand and debug
- **Conditional Routing**: Different paths for escalation, corrections, off-topic handling
- **Extensibility**: Adding new nodes (e.g., sentiment analysis, intent classification) is straightforward
- **Industry Standard**: LangGraph is becoming the standard for agentic workflows

**Graph Flow**:
```
START → check_escalation → check_correction → check_off_topic → extract_field → validate → prompt_next/complete → END
           ↓                     ↓                   ↓
        escalate            extract_field        prompt_next
           ↓                                         ↓
          END                                       END
```

### 2. Pluggable Escalation Handlers

**Decision**: Implement escalation as a plugin system with 5 handler types.

**Handlers**:
| Handler | Purpose | LLM Required |
|---------|---------|--------------|
| `keyword` | Match trigger words | No |
| `timeout` | Session duration limit | No |
| `sentiment` | Detect negative sentiment | Yes |
| `llm_intent` | Classify user intent | Yes |
| `completion` | All required fields collected | No |

**Rationale**:
- **Open/Closed Principle**: New escalation types can be added without modifying existing code
- **Configuration-Driven**: Enable/disable handlers via YAML config
- **Testable**: Each handler can be unit tested independently

### 3. Pydantic for Configuration Validation

**Decision**: Use Pydantic models for all configuration with strict validation.

**Benefits**:
- **Type Safety**: Runtime validation catches configuration errors early
- **Documentation**: Models serve as documentation for config schema
- **Serialization**: Easy YAML/JSON loading and export
- **IDE Support**: Autocomplete and type hints

### 4. State Store Abstraction

**Decision**: Implement `StateStore` as an abstract interface with in-memory implementation.

```python
class StateStore(Protocol):
    def create(self, state: ConversationState) -> str: ...
    def get(self, session_id: str) -> Optional[ConversationState]: ...
    def update(self, state: ConversationState) -> None: ...
    def delete(self, session_id: str) -> None: ...
```

**Rationale**:
- **Future-Proof**: Can swap to Redis, PostgreSQL, or DynamoDB without changing agent logic
- **Testing**: In-memory store is perfect for unit tests
- **No Global State**: Each conversation has its own isolated state

### 5. Async-First Design

**Decision**: All I/O operations are async (LLM calls, API endpoints).

**Benefits**:
- **Concurrency**: Handle multiple conversations simultaneously
- **Non-Blocking**: LLM calls don't block other requests
- **FastAPI Native**: Seamless integration with FastAPI's async support

### 6. LLM Provider Abstraction

**Decision**: Abstract LLM calls behind `LLMProvider` interface.

**Supported Providers**:
- OpenAI (gpt-3.5-turbo, gpt-4, etc.)
- Anthropic (claude-3, etc.)

**Rationale**:
- **Vendor Independence**: Switch providers without code changes
- **Testing**: Easy to mock for unit tests
- **Cost Control**: Can swap to cheaper models for development

---

## Tradeoffs

### 1. LangGraph vs Simple Linear Flow

| Approach | Pros | Cons |
|----------|------|------|
| **LangGraph (chosen)** | Explicit flow, extensible, visual | Learning curve, added dependency |
| **Linear Flow** | Simple, no dependencies | Hard to extend, spaghetti for complex flows |

**Decision**: LangGraph's benefits outweigh the added complexity for this use case.

### 2. In-Memory State vs Database

| Approach | Pros | Cons |
|----------|------|------|
| **In-Memory (chosen)** | Fast, simple, good for demo | Lost on restart, single instance only |
| **Database** | Persistent, scalable | Setup complexity, latency |

**Decision**: Assignment specified in-memory with swappable abstraction. The `StateStore` interface allows easy migration.

### 3. Multiple Packages vs Single Package

| Approach | Pros | Cons |
|----------|------|------|
| **Multiple (chosen)** | Clear boundaries, independent testing | More boilerplate, import complexity |
| **Single** | Simple imports, less setup | Tight coupling, harder to test |

**Decision**: Clear separation aids understanding and testing. The modular structure demonstrates good engineering practices.

### 4. Sync vs Async Correction Detection

| Approach | Pros | Cons |
|----------|------|------|
| **Pattern + LLM (chosen)** | Fast for common cases, accurate for edge cases | Two code paths |
| **LLM Only** | Simpler, more accurate | Slower, more expensive |
| **Pattern Only** | Fast, cheap | Misses nuanced corrections |

**Decision**: Hybrid approach balances speed and accuracy. Common patterns (e.g., "No, my email is...") are detected instantly; ambiguous cases fall back to LLM.

### 5. FastAPI vs Lightweight ASGI

| Approach | Pros | Cons |
|----------|------|------|
| **FastAPI (chosen)** | Auto docs, validation, WebSocket support | Heavier than minimal ASGI |
| **Starlette/ASGI** | Minimal, fast | Manual validation, no auto docs |

**Decision**: FastAPI's developer experience (Swagger UI, validation, typing) justifies the minimal overhead.

---

## What I Would Do With One Additional Day

### Priority 1: Observability & Monitoring

- **Structured Logging**: Add correlation IDs for request tracing
- **Metrics**: Prometheus metrics for LLM latency, escalation rates, completion rates
- **Tracing**: OpenTelemetry integration for distributed tracing

### Priority 2: Enhanced Testing

- **Property-Based Testing**: Use Hypothesis to generate edge-case configurations
- **Load Testing**: Locust scripts for concurrent conversation simulation
- **Integration Tests**: End-to-end tests with real (mocked) LLM responses

### Priority 3: Production Readiness

- **Redis State Store**: Implement Redis backend for horizontal scaling
- **Rate Limiting**: Per-session and per-IP rate limits
- **Health Checks**: Kubernetes-ready liveness and readiness probes
- **Graceful Shutdown**: Handle in-flight conversations during deployment

### Priority 4: Agent Improvements

- **Multi-Turn Context**: Better context window management for long conversations
- **Field Dependencies**: Support conditional fields (e.g., "if country is US, ask for state")
- **Conversation Analytics**: Track completion rates, drop-off points, common corrections

---

## AI Coding Tools Usage

### Tools Used

1. **Claude Code (Anthropic CLI)** - Primary development assistant
2. **GitHub Copilot** - Code completion

### How AI Was Used

#### 1. Architecture Design
- Discussed LangGraph state machine design
- Reviewed tradeoffs between different approaches
- Validated escalation handler plugin architecture

#### 2. Code Generation
- Generated boilerplate for Pydantic models
- Implemented graph nodes and edges
- Created comprehensive test suites

#### 3. Code Review
- AI reviewed code for:
  - Security vulnerabilities
  - Type safety issues
  - Edge case handling
  - Documentation completeness

#### 4. Documentation
- Generated docstrings for all public functions
- Created README sections
- Wrote this DECISIONS.md document

### Human vs AI Contributions

| Area | Human Contribution | AI Contribution |
|------|-------------------|-----------------|
| **Architecture** | High-level design decisions | Implementation details, code structure |
| **Business Logic** | Requirements interpretation | Code implementation |
| **Testing** | Test strategy, edge cases | Test code generation |
| **Documentation** | Review and refinement | Initial drafts |

### Quality Assurance

All AI-generated code was:
1. **Reviewed** for correctness and style
2. **Tested** with comprehensive unit tests (264 tests, 100% coverage target)
3. **Validated** against pre-commit hooks (black, isort, mypy, flake8, bandit)
4. **Manually tested** via API and WebSocket endpoints

---

## Conclusion

This project demonstrates:

1. **Clean Architecture**: Clear separation of concerns with testable, extensible components
2. **Production Patterns**: Async design, state abstraction, configuration validation
3. **Agentic Patterns**: LangGraph state machine, pluggable handlers, LLM abstraction
4. **Engineering Excellence**: Comprehensive testing, pre-commit hooks, documentation

The design prioritizes **extensibility** and **maintainability** while meeting all assignment requirements.
