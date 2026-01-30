"""Request DTOs for invitation operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CreateInvitationRequest(BaseModel):
    """Request to create a new invitation."""

    code: str = Field(..., min_length=6, max_length=32, description="Invitation code")
    created_by: str = Field(..., min_length=1, description="User ID who creates the invitation")
    expires_at: Optional[datetime] = Field(None, description="Expiration date (optional)")
    usage_limit: Optional[int] = Field(
        1, ge=1, description="Maximum number of uses (None = unlimited)"
    )
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        """Validate invitation code format."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Code can only contain alphanumeric characters, hyphens, and underscores"
            )
        return v

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate expiration date is in the future."""
        if v is not None and v <= datetime.utcnow():
            raise ValueError("Expiration date must be in the future")
        return v


class UseInvitationRequest(BaseModel):
    """Request to use an invitation."""

    code: str = Field(..., min_length=6, max_length=32, description="Invitation code to use")
    used_by: str = Field(..., min_length=1, description="User ID who is using the invitation")


class RevokeInvitationRequest(BaseModel):
    """Request to revoke an invitation."""

    invitation_id: str = Field(..., min_length=1, description="Invitation ID to revoke")
    revoked_by: str = Field(..., min_length=1, description="User ID who is revoking")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for revocation")


class ValidateInvitationRequest(BaseModel):
    """Request to validate an invitation code."""

    code: str = Field(..., min_length=6, max_length=32, description="Invitation code to validate")
