"""Value objects for invitation domain."""

import re
from dataclasses import dataclass
from typing import Optional

from invitation_core.domain.exceptions import InvalidInvitationCodeError


@dataclass(frozen=True)
class InvitationCode:
    """Immutable invitation code value object.

    Ensures invitation codes follow business rules:
    - Length between 6 and 32 characters
    - Alphanumeric characters only (optional: allow hyphens/underscores)
    - Case-insensitive comparison
    """

    value: str

    def __post_init__(self) -> None:
        """Validate invitation code on creation."""
        if not self.value:
            raise InvalidInvitationCodeError("Invitation code cannot be empty")

        if len(self.value) < 6:
            raise InvalidInvitationCodeError(
                f"Invitation code must be at least 6 characters long, got {len(self.value)}"
            )

        if len(self.value) > 32:
            raise InvalidInvitationCodeError(
                f"Invitation code must be at most 32 characters long, got {len(self.value)}"
            )

        # Allow alphanumeric, hyphens, and underscores
        if not re.match(r"^[a-zA-Z0-9_-]+$", self.value):
            raise InvalidInvitationCodeError(
                "Invitation code can only contain alphanumeric characters, hyphens, and underscores"
            )

    def __str__(self) -> str:
        """Return uppercase representation."""
        return self.value.upper()

    def __eq__(self, other: object) -> bool:
        """Case-insensitive comparison."""
        if not isinstance(other, InvitationCode):
            return False
        return self.value.upper() == other.value.upper()

    def __hash__(self) -> int:
        """Hash based on uppercase value."""
        return hash(self.value.upper())


@dataclass(frozen=True)
class UsageLimit:
    """Immutable usage limit value object.

    Represents how many times an invitation can be used.
    None means unlimited usage.
    """

    value: Optional[int]

    def __post_init__(self) -> None:
        """Validate usage limit."""
        if self.value is not None and self.value < 0:
            raise ValueError("Usage limit cannot be negative")

    def is_unlimited(self) -> bool:
        """Check if this represents unlimited usage."""
        return self.value is None

    def is_reached(self, current_usage: int) -> bool:
        """Check if the limit has been reached."""
        if self.is_unlimited():
            return False
        return current_usage >= self.value  # type: ignore

    def __str__(self) -> str:
        """String representation."""
        return "unlimited" if self.is_unlimited() else str(self.value)
