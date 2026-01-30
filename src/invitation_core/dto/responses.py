"""Response DTOs for invitation operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from invitation_core.domain.models import Invitation, InvitationStatus


class InvitationResponse(BaseModel):
    """Response containing invitation details."""

    id: str
    code: str
    status: str
    created_by: str
    created_at: datetime
    expires_at: Optional[datetime]
    usage_limit: Optional[int]
    usage_count: int
    used_by: list[str]
    metadata: dict
    revoked_at: Optional[datetime]
    revoked_by: Optional[str]
    revocation_reason: Optional[str]

    @staticmethod
    def from_domain(invitation: Invitation) -> "InvitationResponse":
        """Convert domain model to response DTO."""
        return InvitationResponse(
            id=invitation.id,
            code=str(invitation.code),
            status=invitation.status.value,
            created_by=invitation.created_by,
            created_at=invitation.created_at,
            expires_at=invitation.expires_at,
            usage_limit=invitation.usage_limit.value,
            usage_count=invitation.usage_count,
            used_by=invitation.used_by,
            metadata=invitation.metadata,
            revoked_at=invitation.revoked_at,
            revoked_by=invitation.revoked_by,
            revocation_reason=invitation.revocation_reason,
        )


class InvitationValidationResponse(BaseModel):
    """Response for invitation validation."""

    is_valid: bool = Field(..., description="Whether the invitation is valid")
    code: str = Field(..., description="The invitation code checked")
    status: Optional[str] = Field(None, description="Invitation status if found")
    reason: Optional[str] = Field(None, description="Reason if invalid")
    remaining_uses: Optional[int] = Field(
        None, description="Remaining uses (None = unlimited or invalid)"
    )
    expires_at: Optional[datetime] = Field(None, description="Expiration date if applicable")


class InvitationUsageResponse(BaseModel):
    """Response after using an invitation."""

    invitation_id: str
    code: str
    used_by: str
    usage_count: int
    remaining_uses: Optional[int]
    is_exhausted: bool = Field(..., description="Whether invitation is now exhausted")


class InvitationStatsResponse(BaseModel):
    """Statistics about invitations."""

    total: int
    active: int
    used: int
    expired: int
    revoked: int
