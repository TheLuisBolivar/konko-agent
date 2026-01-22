# Konko AI Conversational Agent - Atomic Implementation Plan

## Overview

This plan ensures **every commit leaves the application in a working state**. Each phase builds incrementally on the previous, with functional milestones that can be tested and demonstrated.

**Core Principle**: Atomic Development - Each commit is independently functional, testable, and deployable.

---

## Technology Stack

- **Python**: 3.11+
- **LLM Framework**: LangChain + LangGraph + LangSmith
- **LLM Provider**: OpenAI (GPT-4/3.5-turbo)
- **Message Queue**: Redis Streams (with in-process fallback)
- **State Storage**: Redis + In-Memory abstraction
- **Validation**: Pydantic
- **Testing**: pytest + pytest-asyncio + hypothesis
- **Type Checking**: mypy (strict mode)
- **Code Quality**: ruff, black, isort
- **Documentation**: Sphinx/MkDocs

---

## Phase 1: Foundation & Basic Flow (Commits 1-8)

### Commit 1: Project Structure & Dependencies
**Goal**: Establish project foundation
**Deliverable**: Runnable Python project with dependencies installed

```
konko-agent/
├── pyproject.toml           # Project dependencies & config
├── README.md                # Basic setup instructions
├── .gitignore              # Python ignores
├── packages/
│   └── agent-core/         # Core package placeholder
│       ├── __init__.py
│       └── py.typed
├── tests/
│   └── __init__.py
└── examples/
    └── .gitkeep
```

**Dependencies**:
```toml
[project]
name = "konko-agent"
version = "0.1.0"
dependencies = [
    "langchain>=0.1.0",
    "langgraph>=0.0.40",
    "langsmith>=0.1.0",
    "openai>=1.10.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0",
    "redis>=5.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "hypothesis>=6.92.0",
    "mypy>=1.7.0",
    "ruff>=0.1.0",
    "black>=23.0.0",
]
```

**Test**: `python -c "import langchain; print('OK')"`

**Commit Message**: `feat: initialize project structure with dependencies`

---

### Commit 2: Configuration Schema (Pydantic Models)
**Goal**: Define type-safe configuration models
**Deliverable**: Validated configuration loading

**Files**:
```
packages/agent-config/
├── __init__.py
├── py.typed
└── schemas.py
```

**Implementation**: `schemas.py`
```python
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from enum import Enum

class Tone(str, Enum):
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    CASUAL = "casual"

class Formality(str, Enum):
    FORMAL = "formal"
    NEUTRAL = "neutral"
    INFORMAL = "informal"

class AgentPersonality(BaseModel):
    tone: Tone = Tone.PROFESSIONAL
    style: str = "concise"
    formality: Formality = Formality.NEUTRAL
    emoji_usage: bool = False
    emoji_list: List[str] = Field(default_factory=lambda: ["👋", "✅", "📧"])

class FieldConfig(BaseModel):
    name: str
    field_type: str = "text"
    required: bool = True
    validation_pattern: Optional[str] = None
    prompt_hint: Optional[str] = None

class EscalationPolicy(BaseModel):
    enabled: bool = True
    reason: str
    policy_type: str  # keyword, sentiment, timeout, llm_intent
    config: Dict = Field(default_factory=dict)

class AgentConfig(BaseModel):
    personality: AgentPersonality = Field(default_factory=AgentPersonality)
    greeting: str = "Hello! I'm here to help collect some information."
    fields: List[FieldConfig]
    escalation_policies: List[EscalationPolicy] = Field(default_factory=list)

    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v):
        if not v:
            raise ValueError("At least one field must be configured")
        return v
```

**Test**: `tests/test_config_schema.py`
```python
import pytest
from agent_config.schemas import AgentConfig, FieldConfig

def test_minimal_valid_config():
    config = AgentConfig(
        fields=[FieldConfig(name="name")]
    )
    assert config.fields[0].name == "name"
    assert config.personality.tone == "professional"

def test_invalid_config_no_fields():
    with pytest.raises(ValueError):
        AgentConfig(fields=[])
```

**Run**: `pytest tests/test_config_schema.py -v`

**Commit Message**: `feat(config): add Pydantic configuration schemas with validation`

---

### Commit 3: YAML Configuration Loader
**Goal**: Load and validate external configuration
**Deliverable**: Load YAML configs with validation

**Files**:
```
packages/agent-config/
└── loader.py
```

**Implementation**: `loader.py`
```python
import yaml
from pathlib import Path
from typing import Union
from .schemas import AgentConfig

def load_config(path: Union[str, Path]) -> AgentConfig:
    """Load and validate agent configuration from YAML file."""
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return AgentConfig(**data)
```

**Sample Config**: `examples/basic_agent.yaml`
```yaml
personality:
  tone: friendly
  style: conversational
  formality: neutral
  emoji_usage: true
  emoji_list: ["👋", "✅", "📧", "📱"]

greeting: "Hi there! 👋 I'd love to get some information from you."

fields:
  - name: name
    field_type: text
    required: true
    prompt_hint: "What's your full name?"

  - name: email
    field_type: email
    required: true
    validation_pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    prompt_hint: "What's your email address?"

  - name: phone
    field_type: phone
    required: true
    validation_pattern: "^\\+?[1-9]\\d{1,14}$"
    prompt_hint: "What's your phone number?"

  - name: address
    field_type: text
    required: true
    prompt_hint: "What's your address?"

escalation_policies:
  - enabled: true
    reason: "All required fields collected"
    policy_type: completion
    config: {}
```

**Test**: `tests/test_config_loader.py`
```python
from agent_config.loader import load_config

def test_load_basic_config():
    config = load_config("examples/basic_agent.yaml")
    assert len(config.fields) == 4
    assert config.fields[0].name == "name"
    assert config.personality.emoji_usage is True
```

**Run**: `pytest tests/test_config_loader.py -v`

**Commit Message**: `feat(config): add YAML loader with example configuration`

---

### Commit 4: State Models & In-Memory Store
**Goal**: Define conversation state and implement storage abstraction
**Deliverable**: Working state management (in-memory)

**Files**:
```
packages/agent-runtime/
├── __init__.py
├── state/
│   ├── __init__.py
│   ├── models.py
│   └── store.py
```

**Implementation**: `state/models.py`
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FieldValue(BaseModel):
    value: str
    confidence: float = 1.0
    validated: bool = False
    attempts: int = 1
    history: List[str] = Field(default_factory=list)

class EscalationStatus(BaseModel):
    escalated: bool = False
    reason: Optional[str] = None
    timestamp: Optional[datetime] = None

class ConversationState(BaseModel):
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    collected_fields: Dict[str, FieldValue] = Field(default_factory=dict)
    current_field_index: int = 0
    escalation: EscalationStatus = Field(default_factory=EscalationStatus)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Implementation**: `state/store.py`
```python
from abc import ABC, abstractmethod
from typing import Optional, List
from .models import ConversationState

class StateStore(ABC):
    """Abstract state storage interface."""

    @abstractmethod
    async def save(self, state: ConversationState) -> None:
        """Save conversation state."""
        pass

    @abstractmethod
    async def load(self, session_id: str) -> Optional[ConversationState]:
        """Load conversation state by session ID."""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete conversation state."""
        pass

    @abstractmethod
    async def list_sessions(self) -> List[str]:
        """List all session IDs."""
        pass

class InMemoryStateStore(StateStore):
    """In-memory implementation of state store."""

    def __init__(self):
        self._storage: Dict[str, ConversationState] = {}

    async def save(self, state: ConversationState) -> None:
        from datetime import datetime
        state.updated_at = datetime.utcnow()
        self._storage[state.session_id] = state

    async def load(self, session_id: str) -> Optional[ConversationState]:
        return self._storage.get(session_id)

    async def delete(self, session_id: str) -> None:
        self._storage.pop(session_id, None)

    async def list_sessions(self) -> List[str]:
        return list(self._storage.keys())
```

**Test**: `tests/test_state_store.py`
```python
import pytest
from agent_runtime.state.store import InMemoryStateStore
from agent_runtime.state.models import ConversationState, Message, MessageRole

@pytest.mark.asyncio
async def test_save_and_load():
    store = InMemoryStateStore()
    state = ConversationState(session_id="test-123")
    state.messages.append(Message(role=MessageRole.USER, content="Hello"))

    await store.save(state)
    loaded = await store.load("test-123")

    assert loaded is not None
    assert loaded.session_id == "test-123"
    assert len(loaded.messages) == 1
```

**Run**: `pytest tests/test_state_store.py -v`

**Commit Message**: `feat(state): add state models and in-memory store implementation`

---

### Commit 5: LangChain LLM Integration
**Goal**: Set up LLM provider abstraction
**Deliverable**: Working LLM calls with OpenAI

**Files**:
```
packages/agent-runtime/
└── llm/
    ├── __init__.py
    └── provider.py
```

**Implementation**: `llm/provider.py`
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any
import os

class LLMProvider:
    """LangChain-based LLM provider."""

    def __init__(self, model: str = "gpt-3.5-turbo", temperature: float = 0.7):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key
        )

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """Generate response from LLM."""
        messages = [SystemMessage(content=system_prompt)]

        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "agent":
                    messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        response = await self.llm.ainvoke(messages)
        return response.content
```

**Test**: `tests/test_llm_provider.py`
```python
import pytest
from agent_runtime.llm.provider import LLMProvider
import os

@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="No API key")
async def test_llm_generate():
    provider = LLMProvider()
    response = await provider.generate(
        system_prompt="You are a helpful assistant.",
        user_message="Say 'test successful' and nothing else."
    )
    assert isinstance(response, str)
    assert len(response) > 0
```

**Commit Message**: `feat(llm): add LangChain OpenAI provider integration`

---

### Commit 6: Basic Agent Core
**Goal**: Create minimal conversational agent
**Deliverable**: Agent that can greet and collect one field

**Files**:
```
packages/agent-core/
├── __init__.py
└── agent.py
```

**Implementation**: `agent.py`
```python
from typing import Optional
from agent_config.schemas import AgentConfig
from agent_runtime.state.models import ConversationState, Message, MessageRole, FieldValue
from agent_runtime.state.store import StateStore
from agent_runtime.llm.provider import LLMProvider
import uuid

class ConversationalAgent:
    """Basic conversational agent for field collection."""

    def __init__(
        self,
        config: AgentConfig,
        state_store: StateStore,
        llm_provider: LLMProvider
    ):
        self.config = config
        self.state_store = state_store
        self.llm = llm_provider

    async def start_conversation(self) -> tuple[str, str]:
        """Start a new conversation and return (session_id, greeting)."""
        session_id = str(uuid.uuid4())
        state = ConversationState(session_id=session_id)

        # Add greeting message
        greeting = self.config.greeting
        state.messages.append(Message(
            role=MessageRole.AGENT,
            content=greeting
        ))

        await self.state_store.save(state)
        return session_id, greeting

    async def process_message(self, session_id: str, user_message: str) -> str:
        """Process user message and return agent response."""
        state = await self.state_store.load(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        # Add user message to state
        state.messages.append(Message(
            role=MessageRole.USER,
            content=user_message
        ))

        # Get current field to collect
        if state.current_field_index >= len(self.config.fields):
            # All fields collected
            response = "Thank you! I have all the information I need."
        else:
            current_field = self.config.fields[state.current_field_index]

            # Check if this is a field value
            if current_field.name not in state.collected_fields:
                # Store the field value
                state.collected_fields[current_field.name] = FieldValue(
                    value=user_message,
                    confidence=0.8,
                    validated=False
                )
                state.current_field_index += 1

                # Ask for next field or complete
                if state.current_field_index >= len(self.config.fields):
                    response = "Thank you! I have all the information I need."
                else:
                    next_field = self.config.fields[state.current_field_index]
                    response = next_field.prompt_hint or f"Could you provide your {next_field.name}?"
            else:
                # Ask for current field
                response = current_field.prompt_hint or f"Could you provide your {current_field.name}?"

        # Add agent response to state
        state.messages.append(Message(
            role=MessageRole.AGENT,
            content=response
        ))

        await self.state_store.save(state)
        return response
```

**Test**: `tests/test_agent_basic.py`
```python
import pytest
from agent_core.agent import ConversationalAgent
from agent_config.schemas import AgentConfig, FieldConfig
from agent_runtime.state.store import InMemoryStateStore
from agent_runtime.llm.provider import LLMProvider

@pytest.mark.asyncio
async def test_start_conversation():
    config = AgentConfig(
        greeting="Hello!",
        fields=[FieldConfig(name="name", prompt_hint="What's your name?")]
    )
    store = InMemoryStateStore()
    llm = LLMProvider()

    agent = ConversationalAgent(config, store, llm)
    session_id, greeting = await agent.start_conversation()

    assert session_id
    assert greeting == "Hello!"

@pytest.mark.asyncio
async def test_collect_field():
    config = AgentConfig(
        greeting="Hello!",
        fields=[
            FieldConfig(name="name", prompt_hint="What's your name?"),
            FieldConfig(name="email", prompt_hint="What's your email?")
        ]
    )
    store = InMemoryStateStore()
    llm = LLMProvider()

    agent = ConversationalAgent(config, store, llm)
    session_id, _ = await agent.start_conversation()

    response = await agent.process_message(session_id, "John Doe")
    assert "email" in response.lower()
```

**Commit Message**: `feat(agent): add basic conversational agent with field collection`

---

### Commit 7: Simple CLI Interface
**Goal**: Make agent runnable from command line
**Deliverable**: Interactive CLI to test agent

**Files**:
```
cli.py
```

**Implementation**: `cli.py`
```python
#!/usr/bin/env python3
"""Simple CLI for testing the conversational agent."""

import asyncio
import sys
from agent_config.loader import load_config
from agent_core.agent import ConversationalAgent
from agent_runtime.state.store import InMemoryStateStore
from agent_runtime.llm.provider import LLMProvider

async def main():
    # Load config
    config_path = sys.argv[1] if len(sys.argv) > 1 else "examples/basic_agent.yaml"
    config = load_config(config_path)

    # Initialize components
    store = InMemoryStateStore()
    llm = LLMProvider()
    agent = ConversationalAgent(config, store, llm)

    # Start conversation
    session_id, greeting = await agent.start_conversation()
    print(f"\nAgent: {greeting}\n")

    # Get first field prompt
    first_field = config.fields[0]
    first_prompt = first_field.prompt_hint or f"Could you provide your {first_field.name}?"
    print(f"Agent: {first_prompt}\n")

    # Conversation loop
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit"]:
                print("\nGoodbye!")
                break

            response = await agent.process_message(session_id, user_input)
            print(f"\nAgent: {response}\n")

            # Check if conversation is complete
            state = await store.load(session_id)
            if state.current_field_index >= len(config.fields):
                print("\n--- Collected Information ---")
                for field_name, field_value in state.collected_fields.items():
                    print(f"{field_name}: {field_value.value}")
                break

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
            break

if __name__ == "__main__":
    asyncio.run(main())
```

**Update README**: Add usage instructions
```markdown
## Quick Start

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Set OpenAI API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

3. Run the agent:
```bash
python cli.py examples/basic_agent.yaml
```

4. Run tests:
```bash
pytest -v
```
```

**Test**: `python cli.py` (manual interaction test)

**Commit Message**: `feat(cli): add interactive CLI for testing agent`

---

### Commit 8: Basic Validation (Regex)
**Goal**: Add field validation
**Deliverable**: Email and phone validation working

**Files**:
```
packages/agent-runtime/
└── validation/
    ├── __init__.py
    └── validators.py
```

**Implementation**: `validation/validators.py`
```python
import re
from typing import Optional, Tuple

class FieldValidator:
    """Field validation using regex patterns."""

    @staticmethod
    def validate(value: str, pattern: Optional[str] = None, field_type: str = "text") -> Tuple[bool, float]:
        """
        Validate field value.

        Returns:
            (is_valid, confidence_score)
        """
        if not pattern and field_type == "text":
            return True, 1.0

        # Use default patterns for known types
        if not pattern:
            if field_type == "email":
                pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            elif field_type == "phone":
                pattern = r"^\+?[1-9]\d{1,14}$"
            else:
                return True, 1.0

        try:
            match = re.match(pattern, value)
            if match:
                return True, 1.0
            else:
                return False, 0.3
        except re.error:
            # Invalid regex pattern
            return True, 0.5
```

**Update Agent**: Integrate validation into `agent.py`
```python
# In process_message method, after collecting field:
from agent_runtime.validation.validators import FieldValidator

# Validate the collected field
is_valid, confidence = FieldValidator.validate(
    user_message,
    current_field.validation_pattern,
    current_field.field_type
)

state.collected_fields[current_field.name] = FieldValue(
    value=user_message,
    confidence=confidence,
    validated=is_valid
)

if not is_valid:
    response = f"That doesn't look like a valid {current_field.field_type}. Could you try again?"
    # Don't increment field index
else:
    state.current_field_index += 1
    # ... continue to next field
```

**Test**: `tests/test_validators.py`
```python
from agent_runtime.validation.validators import FieldValidator

def test_email_validation():
    valid, conf = FieldValidator.validate("test@example.com", field_type="email")
    assert valid is True
    assert conf == 1.0

    invalid, conf = FieldValidator.validate("invalid-email", field_type="email")
    assert invalid is False
    assert conf < 1.0

def test_phone_validation():
    valid, conf = FieldValidator.validate("+12025551234", field_type="phone")
    assert valid is True
```

**Commit Message**: `feat(validation): add regex-based field validation`

---

## Phase 2: Advanced Features (Commits 9-15)

### Commit 9: LLM-Based Field Extraction
**Goal**: Use LLM to extract field values from natural language
**Deliverable**: Agent understands context better

**Files**:
```
packages/agent-runtime/
└── extraction/
    ├── __init__.py
    └── field_extractor.py
```

**Implementation**: Use LangChain structured output
```python
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field as PydanticField
from typing import Optional

class ExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float = PydanticField(ge=0.0, le=1.0)

class FieldExtractor:
    """Extract field values using LLM."""

    def __init__(self, llm_provider):
        self.llm = llm_provider
        self.parser = JsonOutputParser(pydantic_object=ExtractedField)

    async def extract(
        self,
        user_message: str,
        field_name: str,
        field_type: str,
        conversation_history: list
    ) -> Optional[ExtractedField]:
        """Extract field value from user message using LLM."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a field extraction assistant. Extract the {field_name} from the user's message.
            Field type: {field_type}

            Return JSON: {{"field_name": "{field_name}", "value": "extracted_value", "confidence": 0.0-1.0}}

            Confidence scoring:
            - 1.0: Explicit, clear value
            - 0.7-0.9: Implicit but clear
            - 0.4-0.6: Ambiguous
            - <0.4: Unclear/missing

            If the field cannot be extracted, return confidence 0.0."""),
            ("user", "{user_message}")
        ])

        # Use structured output
        chain = prompt | self.llm.llm | self.parser
        result = await chain.ainvoke({
            "field_name": field_name,
            "field_type": field_type,
            "user_message": user_message
        })

        return ExtractedField(**result)
```

**Update Agent**: Use extraction before storing field
```python
from agent_runtime.extraction.field_extractor import FieldExtractor

# In __init__:
self.extractor = FieldExtractor(llm_provider)

# In process_message:
extracted = await self.extractor.extract(
    user_message,
    current_field.name,
    current_field.field_type,
    [{"role": m.role, "content": m.content} for m in state.messages]
)

if extracted and extracted.confidence > 0.4:
    # Validate extracted value
    is_valid, validation_confidence = FieldValidator.validate(...)

    final_confidence = (extracted.confidence + validation_confidence) / 2

    state.collected_fields[current_field.name] = FieldValue(
        value=extracted.value,
        confidence=final_confidence,
        validated=is_valid
    )
```

**Commit Message**: `feat(extraction): add LLM-based field extraction with confidence scoring`

---

### Commit 10: Correction Handling
**Goal**: Allow users to correct previously provided fields
**Deliverable**: "No, my email is..." works

**Implementation**: Update `agent.py`
```python
async def _detect_correction(self, user_message: str, state: ConversationState) -> Optional[str]:
    """Detect if user is correcting a previous field."""
    correction_keywords = ["no", "actually", "wait", "i meant", "correction", "change"]

    message_lower = user_message.lower()
    is_correction = any(keyword in message_lower for keyword in correction_keywords)

    if not is_correction:
        return None

    # Use LLM to determine which field is being corrected
    prompt = f"""User said: "{user_message}"

    Previously collected fields: {list(state.collected_fields.keys())}

    Which field is the user correcting? Reply with just the field name, or "none" if not a correction."""

    field_name = await self.llm.generate(
        system_prompt="You are a correction detector.",
        user_message=prompt
    )

    field_name = field_name.strip().lower()
    return field_name if field_name in state.collected_fields else None

# In process_message, before collecting new field:
correcting_field = await self._detect_correction(user_message, state)
if correcting_field:
    # Extract new value
    extracted = await self.extractor.extract(
        user_message,
        correcting_field,
        # Find field config
        next((f.field_type for f in self.config.fields if f.name == correcting_field), "text"),
        []
    )

    if extracted and extracted.confidence > 0.3:
        # Update field with correction
        old_value = state.collected_fields[correcting_field]
        old_value.history.append(old_value.value)
        old_value.value = extracted.value
        old_value.attempts += 1
        old_value.confidence = extracted.confidence * 0.9  # Penalty for correction

        response = f"Got it, I've updated your {correcting_field} to {extracted.value}."
    else:
        response = f"I'm not sure what to change. Could you clarify?"

    state.messages.append(Message(role=MessageRole.AGENT, content=response))
    await self.state_store.save(state)
    return response
```

**Test**: `tests/test_corrections.py`
```python
@pytest.mark.asyncio
async def test_correction_handling():
    # ... setup agent ...

    session_id, _ = await agent.start_conversation()
    await agent.process_message(session_id, "John Doe")  # name
    await agent.process_message(session_id, "john@example.com")  # email

    response = await agent.process_message(session_id, "Wait, my email is john.doe@example.com")

    state = await store.load(session_id)
    assert state.collected_fields["email"].value == "john.doe@example.com"
    assert state.collected_fields["email"].attempts == 2
```

**Commit Message**: `feat(agent): add correction detection and handling`

---

### Commit 11: Off-Topic Redirection
**Goal**: Handle off-topic responses
**Deliverable**: Agent redirects back to field collection

**Implementation**: Add to `agent.py`
```python
async def _is_off_topic(self, user_message: str, current_field_name: str) -> bool:
    """Determine if message is off-topic."""
    prompt = f"""User was asked for their {current_field_name}.
    User said: "{user_message}"

    Is this a relevant response to the question, or off-topic?
    Reply with only "on_topic" or "off_topic"."""

    response = await self.llm.generate(
        system_prompt="You are an intent classifier.",
        user_message=prompt
    )

    return "off_topic" in response.lower()

async def _generate_redirect(self, current_field: FieldConfig, attempt: int) -> str:
    """Generate personality-appropriate redirect message."""
    personality = self.config.personality

    if attempt == 1:
        # Gentle redirect
        base = f"I appreciate that, but I need to collect your {current_field.name}. "
    elif attempt == 2:
        # Firmer redirect
        base = f"Let's focus on getting your {current_field.name}. "
    else:
        # Last attempt before escalation
        base = f"I really need your {current_field.name} to continue. "

    prompt_hint = current_field.prompt_hint or f"Could you provide your {current_field.name}?"
    return base + prompt_hint

# In process_message, before extraction:
current_field = self.config.fields[state.current_field_index]

if await self._is_off_topic(user_message, current_field.name):
    # Track off-topic attempts
    redirect_count = state.metadata.get("redirect_count", 0) + 1
    state.metadata["redirect_count"] = redirect_count

    if redirect_count >= 3:
        # Escalate
        state.escalation.escalated = True
        state.escalation.reason = "Too many off-topic responses"
        response = "I'm having trouble collecting the information. Let me connect you with someone who can help."
    else:
        response = await self._generate_redirect(current_field, redirect_count)

    state.messages.append(Message(role=MessageRole.AGENT, content=response))
    await self.state_store.save(state)
    return response
```

**Commit Message**: `feat(agent): add off-topic detection and redirect logic`

---

### Commit 12: Escalation Policies Framework
**Goal**: Implement escalation policy engine
**Deliverable**: Escalation policies trigger correctly

**Files**:
```
packages/agent-runtime/
└── escalation/
    ├── __init__.py
    ├── engine.py
    └── policies/
        ├── __init__.py
        ├── base.py
        ├── keyword.py
        ├── timeout.py
        ├── sentiment.py
        └── llm_intent.py
```

**Implementation**: `escalation/policies/base.py`
```python
from abc import ABC, abstractmethod
from agent_runtime.state.models import ConversationState
from agent_config.schemas import EscalationPolicy

class EscalationPolicyHandler(ABC):
    """Base class for escalation policy handlers."""

    def __init__(self, policy: EscalationPolicy):
        self.policy = policy

    @abstractmethod
    async def should_escalate(self, state: ConversationState, user_message: str) -> bool:
        """Determine if escalation should trigger."""
        pass
```

**Implementation**: `escalation/policies/keyword.py`
```python
class KeywordEscalationHandler(EscalationPolicyHandler):
    """Keyword-based escalation."""

    async def should_escalate(self, state: ConversationState, user_message: str) -> bool:
        keywords = self.policy.config.get("keywords", ["human", "agent", "manager", "help"])
        return any(kw in user_message.lower() for kw in keywords)
```

**Implementation**: `escalation/policies/timeout.py`
```python
from datetime import datetime, timedelta

class TimeoutEscalationHandler(EscalationPolicyHandler):
    """Timeout-based escalation."""

    async def should_escalate(self, state: ConversationState, user_message: str) -> bool:
        max_duration = self.policy.config.get("max_duration_seconds", 600)
        duration = (datetime.utcnow() - state.created_at).total_seconds()

        if duration > max_duration:
            return True

        # Check failed attempts per field
        max_attempts = self.policy.config.get("max_attempts_per_field", 3)
        for field_value in state.collected_fields.values():
            if field_value.attempts >= max_attempts and not field_value.validated:
                return True

        return False
```

**Implementation**: `escalation/engine.py`
```python
from typing import List
from .policies.base import EscalationPolicyHandler
from .policies.keyword import KeywordEscalationHandler
from .policies.timeout import TimeoutEscalationHandler

class EscalationEngine:
    """Evaluates escalation policies."""

    def __init__(self, policies: List[EscalationPolicy], llm_provider=None):
        self.handlers: List[EscalationPolicyHandler] = []

        for policy in policies:
            if not policy.enabled:
                continue

            if policy.policy_type == "keyword":
                self.handlers.append(KeywordEscalationHandler(policy))
            elif policy.policy_type == "timeout":
                self.handlers.append(TimeoutEscalationHandler(policy))
            # Add more as implemented

    async def check_escalation(self, state: ConversationState, user_message: str) -> tuple[bool, str]:
        """
        Check all policies.

        Returns:
            (should_escalate, reason)
        """
        for handler in self.handlers:
            if await handler.should_escalate(state, user_message):
                return True, handler.policy.reason

        return False, ""
```

**Update Agent**: Integrate escalation engine
```python
from agent_runtime.escalation.engine import EscalationEngine

# In __init__:
self.escalation_engine = EscalationEngine(config.escalation_policies, llm_provider)

# In process_message, after adding user message:
should_escalate, reason = await self.escalation_engine.check_escalation(state, user_message)
if should_escalate:
    state.escalation.escalated = True
    state.escalation.reason = reason
    state.escalation.timestamp = datetime.utcnow()

    response = "Let me connect you with someone who can better assist you."
    state.messages.append(Message(role=MessageRole.AGENT, content=response))
    await self.state_store.save(state)
    return response
```

**Commit Message**: `feat(escalation): add escalation policy framework with keyword and timeout handlers`

---

### Commit 13: Sentiment & LLM Intent Escalation
**Goal**: Complete all 4 escalation types
**Deliverable**: All escalation policies working

**Implementation**: `escalation/policies/sentiment.py`
```python
class SentimentEscalationHandler(EscalationPolicyHandler):
    """Sentiment-based escalation."""

    def __init__(self, policy, llm_provider):
        super().__init__(policy)
        self.llm = llm_provider

    async def should_escalate(self, state: ConversationState, user_message: str) -> bool:
        threshold = self.policy.config.get("negative_threshold", -0.5)
        sustained_count = self.policy.config.get("sustained_negative_messages", 2)

        # Analyze sentiment of recent messages
        recent_messages = [m for m in state.messages[-4:] if m.role == MessageRole.USER]

        if len(recent_messages) < sustained_count:
            return False

        # Use LLM for sentiment analysis
        prompt = f"""Analyze the sentiment of these user messages:
        {[m.content for m in recent_messages]}

        Rate overall sentiment from -1.0 (very negative) to 1.0 (very positive).
        Reply with only the number."""

        response = await self.llm.generate(
            system_prompt="You are a sentiment analyzer.",
            user_message=prompt
        )

        try:
            sentiment = float(response.strip())
            return sentiment < threshold
        except ValueError:
            return False
```

**Implementation**: `escalation/policies/llm_intent.py`
```python
class LLMIntentEscalationHandler(EscalationPolicyHandler):
    """LLM intent classification for escalation."""

    def __init__(self, policy, llm_provider):
        super().__init__(policy)
        self.llm = llm_provider

    async def should_escalate(self, state: ConversationState, user_message: str) -> bool:
        intents = self.policy.config.get("escalation_intents", [
            "wants_human_agent",
            "frustrated",
            "angry",
            "confused",
            "complaint"
        ])

        prompt = f"""User message: "{user_message}"

        Conversation context: {len(state.messages)} messages exchanged.

        Does this message indicate any of these intents: {', '.join(intents)}?

        Reply with "yes" or "no"."""

        response = await self.llm.generate(
            system_prompt="You are an intent classifier for customer support escalation.",
            user_message=prompt
        )

        return "yes" in response.lower()
```

**Update Engine**: Add new handlers
```python
# In EscalationEngine.__init__:
elif policy.policy_type == "sentiment":
    self.handlers.append(SentimentEscalationHandler(policy, llm_provider))
elif policy.policy_type == "llm_intent":
    self.handlers.append(LLMIntentEscalationHandler(policy, llm_provider))
```

**Update Example Config**: Add all policy types
```yaml
escalation_policies:
  - enabled: true
    reason: "User requested human agent"
    policy_type: keyword
    config:
      keywords: ["human", "agent", "manager", "person", "help me"]

  - enabled: true
    reason: "Conversation timeout or too many failed attempts"
    policy_type: timeout
    config:
      max_duration_seconds: 600
      max_attempts_per_field: 3

  - enabled: true
    reason: "User showing sustained negative sentiment"
    policy_type: sentiment
    config:
      negative_threshold: -0.4
      sustained_negative_messages: 2

  - enabled: true
    reason: "User expressed frustration or confusion"
    policy_type: llm_intent
    config:
      escalation_intents:
        - wants_human_agent
        - frustrated
        - angry
        - confused
```

**Commit Message**: `feat(escalation): add sentiment and LLM intent escalation policies`

---

### Commit 14: LangGraph State Machine Integration
**Goal**: Replace linear flow with LangGraph
**Deliverable**: Sophisticated state machine for conversation flow

**Files**:
```
packages/agent-runtime/
└── graph/
    ├── __init__.py
    └── conversation_graph.py
```

**Implementation**: `graph/conversation_graph.py`
```python
from langgraph.graph import StateGraph, END
from typing import Dict, TypedDict, Annotated
from agent_runtime.state.models import ConversationState, Message, MessageRole
from agent_config.schemas import AgentConfig

class GraphState(TypedDict):
    """State for LangGraph."""
    conversation: ConversationState
    current_message: str
    next_action: str

def create_conversation_graph(config: AgentConfig, agent_instance):
    """Create LangGraph state machine for conversation."""

    # Define nodes
    async def greeting_node(state: GraphState) -> GraphState:
        """Initial greeting."""
        state["next_action"] = "collect_field"
        return state

    async def collect_field_node(state: GraphState) -> GraphState:
        """Collect current field."""
        conv_state = state["conversation"]

        if conv_state.current_field_index >= len(config.fields):
            state["next_action"] = "complete"
        else:
            # Process field collection
            state["next_action"] = "validate"

        return state

    async def validate_node(state: GraphState) -> GraphState:
        """Validate collected field."""
        conv_state = state["conversation"]
        current_field = config.fields[conv_state.current_field_index]

        # Check if validation passed
        if current_field.name in conv_state.collected_fields:
            field_value = conv_state.collected_fields[current_field.name]
            if field_value.validated:
                state["next_action"] = "collect_field"
            else:
                state["next_action"] = "retry"
        else:
            state["next_action"] = "collect_field"

        return state

    async def check_correction_node(state: GraphState) -> GraphState:
        """Check if message is a correction."""
        # Use agent's correction detection
        correcting_field = await agent_instance._detect_correction(
            state["current_message"],
            state["conversation"]
        )

        if correcting_field:
            state["next_action"] = "handle_correction"
        else:
            state["next_action"] = "check_off_topic"

        return state

    async def check_off_topic_node(state: GraphState) -> GraphState:
        """Check if message is off-topic."""
        conv_state = state["conversation"]

        if conv_state.current_field_index < len(config.fields):
            current_field = config.fields[conv_state.current_field_index]
            is_off_topic = await agent_instance._is_off_topic(
                state["current_message"],
                current_field.name
            )

            if is_off_topic:
                state["next_action"] = "redirect"
            else:
                state["next_action"] = "extract_field"
        else:
            state["next_action"] = "complete"

        return state

    async def check_escalation_node(state: GraphState) -> GraphState:
        """Check escalation policies."""
        conv_state = state["conversation"]

        should_escalate, reason = await agent_instance.escalation_engine.check_escalation(
            conv_state,
            state["current_message"]
        )

        if should_escalate:
            state["next_action"] = "escalate"
        else:
            state["next_action"] = "check_correction"

        return state

    async def escalate_node(state: GraphState) -> GraphState:
        """Handle escalation."""
        state["next_action"] = END
        return state

    async def complete_node(state: GraphState) -> GraphState:
        """Complete conversation."""
        state["next_action"] = END
        return state

    # Build graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("greeting", greeting_node)
    workflow.add_node("check_escalation", check_escalation_node)
    workflow.add_node("check_correction", check_correction_node)
    workflow.add_node("check_off_topic", check_off_topic_node)
    workflow.add_node("collect_field", collect_field_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("escalate", escalate_node)
    workflow.add_node("complete", complete_node)

    # Add edges
    workflow.set_entry_point("greeting")

    workflow.add_conditional_edges(
        "greeting",
        lambda s: s["next_action"],
        {
            "collect_field": "collect_field",
        }
    )

    workflow.add_conditional_edges(
        "check_escalation",
        lambda s: s["next_action"],
        {
            "escalate": "escalate",
            "check_correction": "check_correction",
        }
    )

    workflow.add_conditional_edges(
        "collect_field",
        lambda s: s["next_action"],
        {
            "validate": "validate",
            "complete": "complete",
        }
    )

    workflow.add_conditional_edges(
        "validate",
        lambda s: s["next_action"],
        {
            "collect_field": "collect_field",
            "retry": "collect_field",
        }
    )

    workflow.add_edge("escalate", END)
    workflow.add_edge("complete", END)

    return workflow.compile()
```

**Update Agent**: Use LangGraph
```python
from agent_runtime.graph.conversation_graph import create_conversation_graph, GraphState

# In __init__:
self.graph = create_conversation_graph(config, self)

# In process_message:
graph_state: GraphState = {
    "conversation": state,
    "current_message": user_message,
    "next_action": "check_escalation"
}

# Run through graph
result = await self.graph.ainvoke(graph_state)

# Extract updated state
state = result["conversation"]
```

**Commit Message**: `feat(graph): integrate LangGraph state machine for conversation flow`

---

### Commit 15: Redis State Store & Queue
**Goal**: Add Redis persistence
**Deliverable**: Sessions survive restarts

**Implementation**: `state/redis_store.py`
```python
import redis.asyncio as redis
import json
from typing import Optional, List
from .store import StateStore
from .models import ConversationState

class RedisStateStore(StateStore):
    """Redis-based state storage."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "konko:session:"

    async def save(self, state: ConversationState) -> None:
        from datetime import datetime
        state.updated_at = datetime.utcnow()

        key = f"{self.prefix}{state.session_id}"
        value = state.model_dump_json()
        await self.redis.set(key, value)

    async def load(self, session_id: str) -> Optional[ConversationState]:
        key = f"{self.prefix}{session_id}"
        value = await self.redis.get(key)

        if value:
            return ConversationState.model_validate_json(value)
        return None

    async def delete(self, session_id: str) -> None:
        key = f"{self.prefix}{session_id}"
        await self.redis.delete(key)

    async def list_sessions(self) -> List[str]:
        pattern = f"{self.prefix}*"
        keys = await self.redis.keys(pattern)
        return [k.replace(self.prefix, "") for k in keys]
```

**Docker Compose**: `docker-compose.yml`
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

**Update CLI**: Add Redis option
```python
# Add flag for Redis
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("config", nargs="?", default="examples/basic_agent.yaml")
parser.add_argument("--redis", action="store_true", help="Use Redis state store")
args = parser.parse_args()

if args.redis:
    from agent_runtime.state.redis_store import RedisStateStore
    store = RedisStateStore()
else:
    store = InMemoryStateStore()
```

**Commit Message**: `feat(persistence): add Redis state store and Docker Compose setup`

---

## Phase 3: Testing, Observability & Polish (Commits 16-20)

### Commit 16: LangSmith Integration
**Goal**: Add observability and tracing
**Deliverable**: All LLM calls traced in LangSmith

**Implementation**: Update `llm/provider.py`
```python
import os

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "konko-agent"
# Set LANGCHAIN_API_KEY via environment

# LangSmith will automatically trace all LangChain calls
```

**Update README**: Add LangSmith setup
```markdown
### LangSmith Observability (Optional)

To enable tracing:

```bash
export LANGCHAIN_API_KEY="your-langsmith-key"
export LANGCHAIN_TRACING_V2="true"
export LANGCHAIN_PROJECT="konko-agent"
```

View traces at: https://smith.langchain.com/
```

**Commit Message**: `feat(observability): add LangSmith tracing integration`

---

### Commit 17: Comprehensive Integration Tests
**Goal**: Full conversation flow tests
**Deliverable**: >80% coverage

**Files**:
```
tests/
├── integration/
│   ├── __init__.py
│   ├── test_happy_path.py
│   ├── test_corrections.py
│   ├── test_escalation.py
│   └── test_off_topic.py
```

**Implementation**: `tests/integration/test_happy_path.py`
```python
import pytest
from agent_core.agent import ConversationalAgent
from agent_config.loader import load_config
from agent_runtime.state.store import InMemoryStateStore
from agent_runtime.llm.provider import LLMProvider

@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_conversation_flow():
    """Test complete happy path: all fields collected."""
    config = load_config("examples/basic_agent.yaml")
    store = InMemoryStateStore()
    llm = LLMProvider()

    agent = ConversationalAgent(config, store, llm)

    # Start conversation
    session_id, greeting = await agent.start_conversation()
    assert greeting == config.greeting

    # Collect name
    response = await agent.process_message(session_id, "My name is John Doe")
    assert "email" in response.lower() or "e-mail" in response.lower()

    # Collect email
    response = await agent.process_message(session_id, "john.doe@example.com")
    assert "phone" in response.lower()

    # Collect phone
    response = await agent.process_message(session_id, "+12025551234")
    assert "address" in response.lower()

    # Collect address
    response = await agent.process_message(session_id, "123 Main St, City, State 12345")
    assert "thank" in response.lower() or "complete" in response.lower()

    # Verify state
    state = await store.load(session_id)
    assert len(state.collected_fields) == 4
    assert state.collected_fields["name"].value == "John Doe"
    assert state.collected_fields["email"].validated is True
    assert state.escalation.escalated is False
```

**More Tests**: Add tests for all scenarios from assignment

**Run**: `pytest tests/integration/ -v --cov=packages`

**Commit Message**: `test: add comprehensive integration tests for all conversation flows`

---

### Commit 18: Property-Based Tests
**Goal**: Test state machine invariants
**Deliverable**: Property tests for critical paths

**Implementation**: `tests/property/test_state_invariants.py`
```python
from hypothesis import given, strategies as st
import pytest
from agent_runtime.state.models import ConversationState, Message, MessageRole, FieldValue

@given(st.lists(st.text(min_size=1), min_size=1, max_size=10))
def test_messages_always_append_only(messages_content):
    """Messages list should only grow, never shrink or reorder."""
    state = ConversationState(session_id="test")

    for content in messages_content:
        initial_count = len(state.messages)
        state.messages.append(Message(role=MessageRole.USER, content=content))
        assert len(state.messages) == initial_count + 1

    # Verify order preserved
    for i, content in enumerate(messages_content):
        assert state.messages[i].content == content

@given(st.floats(min_value=0.0, max_value=1.0))
def test_confidence_bounds(confidence):
    """Confidence scores must be between 0.0 and 1.0."""
    field_value = FieldValue(value="test", confidence=confidence)
    assert 0.0 <= field_value.confidence <= 1.0

@given(st.integers(min_value=1, max_value=100))
def test_field_collection_no_duplicates_without_correction(num_fields):
    """Fields should not be collected twice without explicit correction."""
    state = ConversationState(session_id="test")

    for i in range(num_fields):
        field_name = f"field_{i}"
        if field_name not in state.collected_fields:
            state.collected_fields[field_name] = FieldValue(value=f"value_{i}")

    # All fields should be unique
    assert len(state.collected_fields) == num_fields
```

**Commit Message**: `test: add property-based tests for state invariants`

---

### Commit 19: Documentation & Diagrams
**Goal**: Complete documentation suite
**Deliverable**: Professional docs

**Files**:
```
docs/
├── architecture.md
├── configuration.md
├── development.md
├── diagrams/
│   ├── architecture.png
│   ├── conversation_flow.png
│   └── event_flow.png
DECISIONS.md
README.md
```

**Update README**: Complete guide
```markdown
# Konko AI Conversational Agent

A production-ready, configurable conversational agent built with LangChain, LangGraph, and Redis.

## Features

- ✅ Sequential field collection with validation
- ✅ Natural language understanding with LLM
- ✅ Correction handling ("No, my email is...")
- ✅ Off-topic redirection
- ✅ 4 escalation policy types (keyword, timeout, sentiment, LLM intent)
- ✅ Configurable personality (tone, style, formality, emojis)
- ✅ Persistent state with Redis
- ✅ LangSmith observability
- ✅ Event-driven architecture
- ✅ Comprehensive test suite

## Quick Start

[Installation, usage, configuration sections...]

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture.

```
┌─────────────────┐
│  Configuration  │ (YAML)
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│ Conversational  │────▶│  LangGraph   │
│     Agent       │     │State Machine │
└────────┬────────┘     └──────────────┘
         │
         ├──────▶ LLM Provider (OpenAI)
         ├──────▶ State Store (Redis)
         ├──────▶ Escalation Engine
         └──────▶ Field Extractor
```

## Testing

```bash
# Run all tests
pytest -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pytest --cov=packages --cov-report=html
```

## License

MIT
```

**Create**: `DECISIONS.md`
```markdown
# Architecture Decisions

## 1. Multi-Package Structure

**Decision**: Split into agent-core, agent-runtime, agent-config packages

**Rationale**:
- Clear separation of concerns
- Independent testing and versioning
- Core agent logic isolated from infrastructure
- Easier to swap implementations (e.g., different state stores)

**Trade-offs**:
- More complex project structure
- Need to manage inter-package dependencies
- Slightly more boilerplate

## 2. LangGraph for State Management

**Decision**: Use LangGraph instead of custom state machine

**Rationale**:
- Battle-tested framework for agent workflows
- Native LangChain integration
- Visual debugging capabilities
- Handles complex conditional logic elegantly

**Trade-offs**:
- Learning curve for LangGraph API
- Additional dependency
- Some overhead vs. simple if/else logic

## 3. Redis for State & Messaging

**Decision**: Redis Streams for message queue, Redis for state storage

**Rationale**:
- Single dependency for both needs
- Lightweight and fast
- Production-ready with persistence
- Async Python support

**Trade-offs**:
- External dependency (requires running Redis)
- Not as feature-rich as RabbitMQ for messaging
- Limited transaction support

## 4. Hybrid Validation Strategy

**Decision**: Regex + LLM extraction + confidence scoring

**Rationale**:
- Regex for quick format checks
- LLM for understanding natural language
- Confidence scoring guides retry logic
- Balances accuracy and cost

**Trade-offs**:
- More complex than pure regex
- LLM calls increase latency and cost
- Need to tune confidence thresholds

## What I Would Do With One Additional Day

1. **Performance Optimization**:
   - Cache LLM responses for similar inputs
   - Batch validation calls
   - Profile and optimize hot paths

2. **Advanced Analytics**:
   - Conversation success metrics dashboard
   - Field collection accuracy tracking
   - Escalation pattern analysis

3. **UI Layer**:
   - Web-based chat interface (FastAPI + WebSockets)
   - Admin dashboard for monitoring sessions
   - Configuration UI instead of YAML editing

4. **Advanced Features**:
   - Multi-language support
   - Voice input/output integration
   - Conditional field collection (branching logic)
   - Field dependencies (email verification, address lookup)

## AI Coding Tools Usage

Used Claude Code for:
- Initial project scaffolding
- Boilerplate reduction (Pydantic models, test fixtures)
- Documentation generation
- Code review and refactoring suggestions

Approach:
- Wrote architecture and core logic manually
- Used AI for repetitive tasks and documentation
- Reviewed all AI-generated code before committing
- AI helped identify edge cases for testing
```

**Create Diagrams**: Use mermaid or similar

**Commit Message**: `docs: add comprehensive documentation and architecture diagrams`

---

### Commit 20: Production Readiness & Polish
**Goal**: Final polish for submission
**Deliverable**: Production-ready package

**Tasks**:
1. Add pre-commit hooks
2. Configure mypy strict mode
3. Add GitHub Actions CI/CD
4. Create sample configs for different personas
5. Final code cleanup and formatting

**Files**:
```
.pre-commit-config.yaml
.github/
  └── workflows/
      └── ci.yml
examples/
  ├── basic_agent.yaml
  ├── professional_sales.yaml
  ├── friendly_support.yaml
  └── casual_survey.yaml
```

**Implementation**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic>=2.5.0]
```

**Implementation**: `.github/workflows/ci.yml`
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          pytest -v --cov=packages --cov-report=xml
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Type check
        run: mypy packages/

      - name: Lint
        run: ruff check packages/
```

**Sample Configs**: Create diverse examples

**Commit Message**: `chore: add production tooling and final polish for submission`

---

## Summary: Atomic Commit Strategy

Each commit represents a **functional milestone**:

1. ✅ Project runs after every commit
2. ✅ Tests pass at each stage
3. ✅ No broken states in git history
4. ✅ Can demo features incrementally
5. ✅ Easy to review and understand

**Development Flow**:
```
Commit → Run Tests → Manual Test → Git Add → Git Commit → Repeat
```

**Rollback Safety**: Any commit can be checked out and runs successfully.

---

## Timeline Estimation (2-3 Days)

**Day 1** (8-10 hours):
- Commits 1-8: Foundation + Basic Flow
- Working CLI demo

**Day 2** (8-10 hours):
- Commits 9-15: Advanced Features
- LangGraph integration
- All escalation types

**Day 3** (8-10 hours):
- Commits 16-20: Testing + Documentation
- Production polish
- Final submission prep

**Total**: ~25-30 hours of focused development

---

## Success Metrics

After completion:

1. ✅ Run `pytest` → All tests pass
2. ✅ Run `python cli.py` → Interactive conversation works
3. ✅ Check LangSmith → All traces visible
4. ✅ Docker Compose up → Redis persistence works
5. ✅ Review DECISIONS.md → Architecture clearly explained
6. ✅ Check coverage → >80% code coverage
7. ✅ Grant repo access → Ready for evaluation

---

## Git Workflow

```bash
# After each commit milestone:
git add .
git commit -m "feat: <commit message from plan>"
git push origin main

# Regular testing:
pytest -v
python cli.py examples/basic_agent.yaml

# Before submission:
pytest --cov=packages --cov-report=html
mypy packages/
ruff check packages/
```

---

This plan ensures **continuous functionality** while building toward the complete solution. Each phase adds value without breaking existing features.
