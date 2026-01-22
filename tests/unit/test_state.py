"""Tests for conversation state models."""

from datetime import datetime, timedelta

from agent_runtime import ConversationState, ConversationStatus, FieldValue, Message, MessageRole


class TestMessage:
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a basic message."""
        message = Message(role=MessageRole.USER, content="Hello!")

        assert message.role == MessageRole.USER
        assert message.content == "Hello!"
        assert message.id  # Should have auto-generated ID
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}

    def test_message_with_metadata(self):
        """Test creating a message with metadata."""
        metadata = {"intent": "greeting", "confidence": 0.95}
        message = Message(role=MessageRole.AGENT, content="Hi there!", metadata=metadata)

        assert message.metadata == metadata


class TestFieldValue:
    """Tests for FieldValue model."""

    def test_create_field_value(self):
        """Test creating a field value."""
        field = FieldValue(field_name="email")

        assert field.field_name == "email"
        assert field.value is None
        assert field.is_valid is False
        assert field.attempts == 0
        assert field.last_attempt_timestamp is None

    def test_field_value_with_data(self):
        """Test creating a field value with data."""
        now = datetime.utcnow()
        field = FieldValue(
            field_name="email",
            value="test@example.com",
            is_valid=True,
            attempts=1,
            last_attempt_timestamp=now,
        )

        assert field.value == "test@example.com"
        assert field.is_valid is True
        assert field.attempts == 1
        assert field.last_attempt_timestamp == now


class TestConversationState:
    """Tests for ConversationState model."""

    def test_create_default_state(self):
        """Test creating a conversation state with defaults."""
        state = ConversationState()

        assert state.session_id  # Should have auto-generated ID
        assert state.status == ConversationStatus.ACTIVE
        assert len(state.messages) == 0
        assert len(state.collected_fields) == 0
        assert state.current_field is None
        assert state.escalation_triggered is False
        assert isinstance(state.started_at, datetime)
        assert isinstance(state.updated_at, datetime)
        assert state.ended_at is None

    def test_add_message(self):
        """Test adding messages to conversation."""
        state = ConversationState()

        msg1 = state.add_message(MessageRole.AGENT, "Hello!")
        msg2 = state.add_message(MessageRole.USER, "Hi there!")

        assert len(state.messages) == 2
        assert state.messages[0].content == "Hello!"
        assert state.messages[1].content == "Hi there!"
        assert msg1.role == MessageRole.AGENT
        assert msg2.role == MessageRole.USER

    def test_add_message_with_metadata(self):
        """Test adding a message with metadata."""
        state = ConversationState()

        msg = state.add_message(
            MessageRole.AGENT, "Please enter your email", intent="collect_field"
        )

        assert msg.metadata["intent"] == "collect_field"

    def test_update_field_value(self):
        """Test updating field values."""
        state = ConversationState()

        field = state.update_field_value("email", "test@example.com", True)

        assert field.field_name == "email"
        assert field.value == "test@example.com"
        assert field.is_valid is True
        assert field.attempts == 1
        assert field.last_attempt_timestamp is not None

    def test_update_field_value_multiple_attempts(self):
        """Test multiple attempts to update field value."""
        state = ConversationState()

        state.update_field_value("email", "invalid", False)
        state.update_field_value("email", "test@example.com", True)

        field = state.collected_fields["email"]
        assert field.attempts == 2
        assert field.value == "test@example.com"
        assert field.is_valid is True

    def test_get_collected_data(self):
        """Test retrieving collected data."""
        state = ConversationState()

        state.update_field_value("name", "John", True)
        state.update_field_value("email", "john@example.com", True)
        state.update_field_value("phone", "invalid", False)  # Invalid, shouldn't be included

        data = state.get_collected_data()

        assert data == {"name": "John", "email": "john@example.com"}
        assert "phone" not in data

    def test_get_missing_fields(self):
        """Test identifying missing required fields."""
        state = ConversationState()

        state.update_field_value("name", "John", True)

        required = ["name", "email", "phone"]
        missing = state.get_missing_fields(required)

        assert set(missing) == {"email", "phone"}

    def test_mark_escalated(self):
        """Test marking conversation as escalated."""
        state = ConversationState()

        state.mark_escalated("User requested human agent", "policy_123")

        assert state.status == ConversationStatus.ESCALATED
        assert state.escalation_triggered is True
        assert state.escalation_reason == "User requested human agent"
        assert state.escalation_policy_id == "policy_123"
        assert state.ended_at is not None

    def test_mark_completed(self):
        """Test marking conversation as completed."""
        state = ConversationState()

        state.mark_completed()

        assert state.status == ConversationStatus.COMPLETED
        assert state.ended_at is not None

    def test_mark_failed(self):
        """Test marking conversation as failed."""
        state = ConversationState()

        state.mark_failed("Network error")

        assert state.status == ConversationStatus.FAILED
        assert state.metadata["failure_reason"] == "Network error"
        assert state.ended_at is not None

    def test_get_duration_seconds_active(self):
        """Test getting duration for active conversation."""
        state = ConversationState()

        duration = state.get_duration_seconds()

        assert duration >= 0
        assert duration < 1  # Should be very recent

    def test_get_duration_seconds_ended(self):
        """Test getting duration for ended conversation."""
        state = ConversationState()
        state.started_at = datetime.utcnow() - timedelta(minutes=5)
        state.mark_completed()

        duration = state.get_duration_seconds()

        assert duration >= 300  # At least 5 minutes
        assert duration < 301  # Should be close to 5 minutes


class TestEnums:
    """Tests for enum types."""

    def test_message_role_enum(self):
        """Test MessageRole enum values."""
        assert MessageRole.AGENT == "agent"
        assert MessageRole.USER == "user"
        assert MessageRole.SYSTEM == "system"

    def test_conversation_status_enum(self):
        """Test ConversationStatus enum values."""
        assert ConversationStatus.ACTIVE == "active"
        assert ConversationStatus.COMPLETED == "completed"
        assert ConversationStatus.ESCALATED == "escalated"
        assert ConversationStatus.FAILED == "failed"
