"""Tests for state store."""

from datetime import datetime, timedelta, timezone
from threading import Thread

import pytest
from agent_runtime import ConversationState, ConversationStatus
from agent_runtime.store import StateStore, get_default_store, set_default_store


class TestStateStore:
    """Tests for StateStore class."""

    @pytest.fixture
    def store(self):
        """Create a fresh store for each test."""
        return StateStore()

    @pytest.fixture
    def sample_state(self):
        """Create a sample conversation state."""
        return ConversationState(session_id="test-session-123")

    def test_create_state(self, store, sample_state):
        """Test creating a new state."""
        created = store.create(sample_state)

        assert created.session_id == sample_state.session_id
        assert store.get(sample_state.session_id) == created

    def test_create_duplicate_fails(self, store, sample_state):
        """Test that creating duplicate state raises error."""
        store.create(sample_state)

        with pytest.raises(ValueError) as exc_info:
            store.create(sample_state)

        assert "already exists" in str(exc_info.value)

    def test_get_existing_state(self, store, sample_state):
        """Test retrieving existing state."""
        store.create(sample_state)

        retrieved = store.get(sample_state.session_id)

        assert retrieved is not None
        assert retrieved.session_id == sample_state.session_id

    def test_get_nonexistent_state(self, store):
        """Test retrieving non-existent state returns None."""
        result = store.get("nonexistent-session")

        assert result is None

    def test_update_state(self, store, sample_state):
        """Test updating an existing state."""
        store.create(sample_state)

        sample_state.add_message("user", "Hello!")
        updated = store.update(sample_state)

        assert len(updated.messages) == 1
        assert updated.updated_at >= sample_state.started_at

    def test_update_nonexistent_fails(self, store, sample_state):
        """Test updating non-existent state raises error."""
        with pytest.raises(ValueError) as exc_info:
            store.update(sample_state)

        assert "not found" in str(exc_info.value)

    def test_delete_state(self, store, sample_state):
        """Test deleting a state."""
        store.create(sample_state)

        deleted = store.delete(sample_state.session_id)

        assert deleted is True
        assert store.get(sample_state.session_id) is None

    def test_delete_nonexistent(self, store):
        """Test deleting non-existent state returns False."""
        deleted = store.delete("nonexistent-session")

        assert deleted is False

    def test_list_all_states(self, store):
        """Test listing all states."""
        state1 = ConversationState(session_id="session-1")
        state2 = ConversationState(session_id="session-2")
        state3 = ConversationState(session_id="session-3")

        store.create(state1)
        store.create(state2)
        store.create(state3)

        states = store.list()

        assert len(states) == 3
        session_ids = {s.session_id for s in states}
        assert session_ids == {"session-1", "session-2", "session-3"}

    def test_list_with_status_filter(self, store):
        """Test listing states with status filter."""
        active_state = ConversationState(session_id="active")
        completed_state = ConversationState(session_id="completed")
        completed_state.mark_completed()

        store.create(active_state)
        store.create(completed_state)

        active_states = store.list(status=ConversationStatus.ACTIVE)
        completed_states = store.list(status=ConversationStatus.COMPLETED)

        assert len(active_states) == 1
        assert active_states[0].session_id == "active"
        assert len(completed_states) == 1
        assert completed_states[0].session_id == "completed"

    def test_list_with_limit(self, store):
        """Test listing states with limit."""
        for i in range(5):
            store.create(ConversationState(session_id=f"session-{i}"))

        states = store.list(limit=3)

        assert len(states) == 3

    def test_list_ordered_by_updated_at(self, store):
        """Test that list returns states ordered by updated_at descending."""
        state1 = ConversationState(session_id="session-1")
        state2 = ConversationState(session_id="session-2")
        state3 = ConversationState(session_id="session-3")

        # Create in order
        store.create(state1)
        store.create(state2)
        store.create(state3)

        # Update state1 to make it most recent
        state1.add_message("user", "Hello!")
        store.update(state1)

        states = store.list()

        # state1 should be first because it was updated most recently
        assert states[0].session_id == "session-1"

    def test_count_all(self, store):
        """Test counting all states."""
        for i in range(5):
            store.create(ConversationState(session_id=f"session-{i}"))

        count = store.count()

        assert count == 5

    def test_count_with_status(self, store):
        """Test counting states with status filter."""
        for i in range(3):
            store.create(ConversationState(session_id=f"active-{i}"))

        for i in range(2):
            state = ConversationState(session_id=f"completed-{i}")
            state.mark_completed()
            store.create(state)

        active_count = store.count(status=ConversationStatus.ACTIVE)
        completed_count = store.count(status=ConversationStatus.COMPLETED)

        assert active_count == 3
        assert completed_count == 2

    def test_clear(self, store):
        """Test clearing all states."""
        for i in range(5):
            store.create(ConversationState(session_id=f"session-{i}"))

        cleared = store.clear()

        assert cleared == 5
        assert store.count() == 0

    def test_get_active_sessions(self, store):
        """Test getting active session IDs."""
        active1 = ConversationState(session_id="active-1")
        active2 = ConversationState(session_id="active-2")
        completed = ConversationState(session_id="completed")
        completed.mark_completed()

        store.create(active1)
        store.create(active2)
        store.create(completed)

        active_sessions = store.get_active_sessions()

        assert set(active_sessions) == {"active-1", "active-2"}

    def test_cleanup_old_sessions(self, store):
        """Test cleaning up old sessions."""
        # Create an old completed session
        old_state = ConversationState(session_id="old")
        old_state.mark_completed()
        old_state.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        store.create(old_state)

        # Create a recent completed session
        recent_state = ConversationState(session_id="recent")
        recent_state.mark_completed()
        store.create(recent_state)

        # Create an old but still active session (should not be cleaned)
        active_state = ConversationState(session_id="active")
        active_state.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
        store.create(active_state)

        # Clean up sessions older than 1 hour
        cleaned = store.cleanup_old_sessions(max_age_seconds=3600)

        assert cleaned == 1  # Only the old completed session
        assert store.get("old") is None
        assert store.get("recent") is not None
        assert store.get("active") is not None

    def test_thread_safety(self, store):
        """Test that store operations are thread-safe."""
        num_threads = 10
        states_per_thread = 10

        def create_states(thread_id):
            for i in range(states_per_thread):
                state = ConversationState(session_id=f"thread-{thread_id}-state-{i}")
                store.create(state)

        threads = []
        for i in range(num_threads):
            thread = Thread(target=create_states, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have created all states without errors
        total_expected = num_threads * states_per_thread
        assert store.count() == total_expected


class TestDefaultStore:
    """Tests for default store management."""

    def test_get_default_store(self):
        """Test getting default store instance."""
        store1 = get_default_store()
        store2 = get_default_store()

        # Should return the same instance
        assert store1 is store2

    def test_set_default_store(self):
        """Test setting a custom default store."""
        custom_store = StateStore()
        set_default_store(custom_store)

        retrieved = get_default_store()

        assert retrieved is custom_store

    def test_default_store_persistence(self):
        """Test that default store persists data between calls."""
        store = get_default_store()
        state = ConversationState(session_id="test-persistence")
        store.create(state)

        # Get store again and check if state is still there
        store2 = get_default_store()
        retrieved = store2.get("test-persistence")

        assert retrieved is not None
        assert retrieved.session_id == "test-persistence"

        # Cleanup
        store.clear()
