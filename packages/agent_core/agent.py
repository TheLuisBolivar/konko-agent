"""Conversational Agent Core for AI Agent.

This module provides the main agent logic for conducting conversations,
collecting information, and managing the conversation flow.
"""

from typing import Optional

from agent_config import AgentConfig, FieldConfig
from agent_runtime import ConversationState, MessageRole, StateStore

from .llm_provider import LLMProvider, LLMProviderError


class AgentError(Exception):
    """Raised when there's an error with the agent."""

    pass


class ConversationalAgent:
    """Main conversational agent that manages dialogue and field collection."""

    def __init__(
        self,
        config: AgentConfig,
        store: StateStore,
        llm_provider: Optional[LLMProvider] = None,
    ):
        """Initialize the conversational agent.

        Args:
            config: Agent configuration
            store: State store for managing conversation state
            llm_provider: Optional LLM provider (created from config if not provided)
        """
        self.config = config
        self.store = store
        self._llm_provider = llm_provider

    @property
    def llm_provider(self) -> LLMProvider:
        """Get or create the LLM provider.

        Returns:
            LLM provider instance
        """
        if self._llm_provider is None:
            self._llm_provider = LLMProvider(self.config.llm)
        return self._llm_provider

    def start_conversation(self) -> ConversationState:
        """Start a new conversation and return the initial state.

        Returns:
            New conversation state with greeting message
        """
        state = ConversationState()
        state.add_message(MessageRole.AGENT, self.config.greeting)
        self.store.create(state)
        return state

    def get_next_field_to_collect(self, state: ConversationState) -> Optional[FieldConfig]:
        """Get the next field that needs to be collected.

        Args:
            state: Current conversation state

        Returns:
            Next field to collect, or None if all fields are collected
        """
        collected_fields = set(state.get_collected_data().keys())

        for field in self.config.fields:
            if field.required and field.name not in collected_fields:
                return field

        # Check optional fields
        for field in self.config.fields:
            if not field.required and field.name not in collected_fields:
                return field

        return None

    def _build_system_prompt(self) -> str:
        """Build the system prompt based on agent personality.

        Returns:
            System prompt string
        """
        personality = self.config.personality

        prompt_parts = [
            "You are a conversational AI assistant helping to collect information.",
            f"Your tone should be {personality.tone.value}.",
            f"Your communication style is {personality.style}.",
            f"Your formality level is {personality.formality.value}.",
        ]

        if personality.emoji_usage:
            emojis = ", ".join(personality.emoji_list[:5])
            prompt_parts.append(f"You may use emojis like: {emojis}")
        else:
            prompt_parts.append("Do not use emojis in your responses.")

        prompt_parts.extend(
            [
                "",
                "Guidelines:",
                "- Be helpful and guide the user through the information collection process.",
                "- Ask for one piece of information at a time.",
                "- Validate information when appropriate.",
                "- Be patient and understanding if the user makes mistakes.",
                "- Keep responses concise but friendly.",
            ]
        )

        return "\n".join(prompt_parts)

    def _build_field_prompt(self, field: FieldConfig, state: ConversationState) -> str:
        """Build a prompt to ask for a specific field.

        Args:
            field: Field configuration to ask about
            state: Current conversation state

        Returns:
            Prompt string for the LLM
        """
        collected_data = state.get_collected_data()
        system_prompt = self._build_system_prompt()

        context_parts = [
            system_prompt,
            "",
            "Current conversation context:",
        ]

        # Add recent messages for context (last 6 messages)
        recent_messages = state.messages[-6:] if len(state.messages) > 6 else state.messages
        for msg in recent_messages:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            context_parts.append(f"{role}: {msg.content}")

        context_parts.extend(
            [
                "",
                f"Already collected information: {collected_data}",
                "",
                f"Next field to collect: {field.name} (type: {field.field_type})",
            ]
        )

        if field.prompt_hint:
            context_parts.append(f"Hint for asking: {field.prompt_hint}")

        context_parts.extend(
            [
                "",
                "Generate a natural response asking for this information.",
                "Keep it brief and conversational.",
            ]
        )

        return "\n".join(context_parts)

    def _build_extraction_prompt(
        self, field: FieldConfig, user_message: str, state: ConversationState
    ) -> str:
        """Build a prompt to extract field value from user message.

        Args:
            field: Field configuration to extract
            user_message: User's message
            state: Current conversation state

        Returns:
            Prompt string for extraction
        """
        return f"""Extract the {field.name} ({field.field_type}) from the user's message.

User message: "{user_message}"

Field to extract: {field.name}
Field type: {field.field_type}
Required: {field.required}

Instructions:
- If the user provided a valid {field.field_type}, respond with ONLY the extracted value.
- If the user did not provide this information or it's unclear, respond with "NOT_PROVIDED".
- If the value seems invalid for the field type, respond with "INVALID".
- Do not include any other text, just the value or status.

Response:"""

    def _validate_field_value(self, field: FieldConfig, value: str) -> bool:
        """Validate a field value against its type and pattern.

        Args:
            field: Field configuration
            value: Value to validate

        Returns:
            True if valid, False otherwise
        """
        if not value or value in ("NOT_PROVIDED", "INVALID"):
            return False

        # Type-specific validation
        validators = {
            "email": self._validate_email,
            "phone": self._validate_phone,
            "url": self._validate_url,
            "number": self._validate_number,
        }

        validator = validators.get(field.field_type)
        if validator and not validator(value):
            return False

        # Custom validation pattern
        if field.validation_pattern and not self._match_pattern(field.validation_pattern, value):
            return False

        return True

    def _validate_email(self, value: str) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))

    def _validate_phone(self, value: str) -> bool:
        """Validate phone number format."""
        import re

        pattern = r"^[\d\s\-\(\)\+]+$"
        digits_only = re.sub(r"\D", "", value)
        return bool(re.match(pattern, value)) and len(digits_only) >= 7

    def _validate_url(self, value: str) -> bool:
        """Validate URL format."""
        import re

        pattern = r"^https?://[^\s]+$"
        return bool(re.match(pattern, value))

    def _validate_number(self, value: str) -> bool:
        """Validate numeric value."""
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _match_pattern(self, pattern: str, value: str) -> bool:
        """Match value against regex pattern."""
        import re

        return bool(re.match(pattern, value))

    async def process_message(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        """Process a user message and generate a response.

        Args:
            state: Current conversation state
            user_message: User's message

        Returns:
            Tuple of (assistant response, updated state)

        Raises:
            AgentError: If there's an error processing the message
        """
        try:
            # Add user message to state
            state.add_message(MessageRole.USER, user_message)

            # Get next field to collect
            next_field = self.get_next_field_to_collect(state)

            if next_field:
                # Try to extract field value from user message
                extraction_prompt = self._build_extraction_prompt(next_field, user_message, state)
                extracted_value = await self.llm_provider.ainvoke(extraction_prompt)
                extracted_value = extracted_value.strip()

                # Validate and store if valid
                if self._validate_field_value(next_field, extracted_value):
                    state.update_field_value(next_field.name, extracted_value, True)

                # Check if there are more fields to collect
                next_field = self.get_next_field_to_collect(state)

            if next_field:
                # Ask for next field
                field_prompt = self._build_field_prompt(next_field, state)
                response = await self.llm_provider.ainvoke(field_prompt)
            else:
                # All fields collected - generate completion message
                collected_data = state.get_collected_data()
                completion_prompt = f"""{self._build_system_prompt()}

All required information has been collected:
{collected_data}

Generate a brief, friendly thank you message confirming the information was received.
Keep it short (1-2 sentences)."""

                response = await self.llm_provider.ainvoke(completion_prompt)
                state.mark_completed()

            # Add assistant response to state
            state.add_message(MessageRole.AGENT, response)

            # Update state in store
            self.store.update(state)

            return response, state

        except LLMProviderError as e:
            raise AgentError(f"LLM error: {str(e)}") from e
        except Exception as e:
            raise AgentError(f"Error processing message: {str(e)}") from e

    def process_message_sync(
        self, state: ConversationState, user_message: str
    ) -> tuple[str, ConversationState]:
        """Process a user message synchronously.

        Args:
            state: Current conversation state
            user_message: User's message

        Returns:
            Tuple of (assistant response, updated state)
        """
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.process_message(state, user_message)
        )
