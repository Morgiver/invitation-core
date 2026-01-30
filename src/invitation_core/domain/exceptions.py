"""Domain exceptions for invitation management."""


class InvitationDomainError(Exception):
    """Base exception for all invitation domain errors."""

    pass


class InvitationNotFoundError(InvitationDomainError):
    """Raised when an invitation is not found."""

    pass


class InvitationAlreadyUsedError(InvitationDomainError):
    """Raised when attempting to use an already used invitation."""

    pass


class InvitationExpiredError(InvitationDomainError):
    """Raised when attempting to use an expired invitation."""

    pass


class InvitationLimitReachedError(InvitationDomainError):
    """Raised when invitation usage limit has been reached."""

    pass


class InvalidInvitationCodeError(InvitationDomainError):
    """Raised when an invitation code is invalid."""

    pass


class InvitationAlreadyExistsError(InvitationDomainError):
    """Raised when attempting to create an invitation with a code that already exists."""

    pass
