"""Protocol-style service abstractions.

Use these interfaces for dependency injection so new modules can be added with
minimal changes to existing service implementations.
"""

from typing import Any, Protocol


class UserService(Protocol):
    async def get_user(self, user_id: int) -> dict[str, Any] | None:
        """Fetch a user by telegram ID."""

    async def upsert_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """Create or update user data."""


class AnalyticsService(Protocol):
    async def track_event(self, event_name: str, payload: dict[str, Any]) -> None:
        """Track an analytics event."""


class PremiumService(Protocol):
    async def has_access(self, user_id: int) -> bool:
        """Return True if user has premium access."""
