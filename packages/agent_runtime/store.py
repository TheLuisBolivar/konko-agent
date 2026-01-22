"""In-memory state store for Konko AI Agent.

This module provides an in-memory implementation of state storage.
For production use, this can be replaced with Redis or another persistent store.
"""

from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional

from .state import ConversationState, ConversationStatus


class StateStore:
    """In-memory store for conversation state.

    This implementation uses a simple dictionary with thread-safe access.
    For production, consider using Redis or another distributed store.
    """

    def __init__(self) -> None:
        """Initialize the state store."""
        self._states: Dict[str, ConversationState] = {}
        self._lock = Lock()

    def create(self, state: ConversationState) -> ConversationState:
        """Create a new conversation state.

        Args:
            state: ConversationState to store

        Returns:
            The stored ConversationState

        Raises:
            ValueError: If a state with this session_id already exists
        """
        with self._lock:
            if state.session_id in self._states:
                raise ValueError(f"State with session_id {state.session_id} already exists")

            self._states[state.session_id] = state
            return state

    def get(self, session_id: str) -> Optional[ConversationState]:
        """Retrieve a conversation state by session ID.

        Args:
            session_id: Session ID to look up

        Returns:
            ConversationState if found, None otherwise
        """
        with self._lock:
            return self._states.get(session_id)

    def update(self, state: ConversationState) -> ConversationState:
        """Update an existing conversation state.

        Args:
            state: ConversationState to update

        Returns:
            The updated ConversationState

        Raises:
            ValueError: If the state doesn't exist
        """
        with self._lock:
            if state.session_id not in self._states:
                raise ValueError(f"State with session_id {state.session_id} not found")

            state.updated_at = datetime.utcnow()
            self._states[state.session_id] = state
            return state

    def delete(self, session_id: str) -> bool:
        """Delete a conversation state.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if session_id in self._states:
                del self._states[session_id]
                return True
            return False

    def list(
        self,
        status: Optional[ConversationStatus] = None,
        limit: Optional[int] = None,
    ) -> List[ConversationState]:
        """List conversation states with optional filtering.

        Args:
            status: Optional status filter
            limit: Optional limit on number of results

        Returns:
            List of ConversationState objects matching the criteria
        """
        with self._lock:
            states = list(self._states.values())

            # Filter by status if provided
            if status is not None:
                states = [s for s in states if s.status == status]

            # Sort by updated_at descending (most recent first)
            states.sort(key=lambda s: s.updated_at, reverse=True)

            # Apply limit if provided
            if limit is not None:
                states = states[:limit]

            return states

    def count(self, status: Optional[ConversationStatus] = None) -> int:
        """Count conversation states with optional filtering.

        Args:
            status: Optional status filter

        Returns:
            Count of states matching the criteria
        """
        with self._lock:
            if status is None:
                return len(self._states)

            return sum(1 for s in self._states.values() if s.status == status)

    def clear(self) -> int:
        """Clear all states from the store.

        Returns:
            Number of states cleared
        """
        with self._lock:
            count = len(self._states)
            self._states.clear()
            return count

    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs.

        Returns:
            List of session IDs with ACTIVE status
        """
        with self._lock:
            return [
                session_id
                for session_id, state in self._states.items()
                if state.status == ConversationStatus.ACTIVE
            ]

    def cleanup_old_sessions(self, max_age_seconds: int) -> int:
        """Clean up old completed/failed sessions.

        Args:
            max_age_seconds: Maximum age in seconds for completed/failed sessions

        Returns:
            Number of sessions cleaned up
        """
        with self._lock:
            now = datetime.utcnow()
            to_delete = []

            for session_id, state in self._states.items():
                # Only clean up non-active sessions
                if state.status == ConversationStatus.ACTIVE:
                    continue

                # Calculate age
                age_seconds = (now - state.updated_at).total_seconds()
                if age_seconds > max_age_seconds:
                    to_delete.append(session_id)

            # Delete old sessions
            for session_id in to_delete:
                del self._states[session_id]

            return len(to_delete)


# Global singleton instance for convenience
_default_store: Optional[StateStore] = None


def get_default_store() -> StateStore:
    """Get the default global state store instance.

    Returns:
        The default StateStore instance
    """
    global _default_store
    if _default_store is None:
        _default_store = StateStore()
    return _default_store


def set_default_store(store: StateStore) -> None:
    """Set the default global state store instance.

    Args:
        store: StateStore instance to use as default
    """
    global _default_store
    _default_store = store
