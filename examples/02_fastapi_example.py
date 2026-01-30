"""FastAPI integration example for invitation-core.

This example shows how to integrate invitation-core with FastAPI.

Run with:
    pip install fastapi uvicorn
    uvicorn examples.02_fastapi_example:app --reload
"""

from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from invitation_core import (
    CreateInvitationRequest,
    InvitationNotFoundError,
    InvitationService,
    UseInvitationRequest,
    ValidateInvitationRequest,
)
from invitation_core.adapters import InMemoryEventBus, InMemoryInvitationRepository

# Initialize FastAPI app
app = FastAPI(title="Invitation API", version="1.0.0")

# Global service instance (in production, use dependency injection)
_repository = InMemoryInvitationRepository()
_event_bus = InMemoryEventBus()
_service = InvitationService(_repository, _event_bus)


def get_invitation_service() -> InvitationService:
    """Dependency for getting invitation service."""
    return _service


# Request/Response models for API
class CreateInvitationAPIRequest(BaseModel):
    """API request model for creating invitations."""

    code: str
    created_by: str
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = 1
    metadata: dict = {}


class UseInvitationAPIRequest(BaseModel):
    """API request model for using invitations."""

    code: str
    used_by: str


# API Endpoints


@app.post("/invitations")
def create_invitation(
    request: CreateInvitationAPIRequest,
    service: InvitationService = Depends(get_invitation_service),
):
    """Create a new invitation code."""
    try:
        invitation_request = CreateInvitationRequest(
            code=request.code,
            created_by=request.created_by,
            expires_at=request.expires_at,
            usage_limit=request.usage_limit,
            metadata=request.metadata,
        )
        result = service.create_invitation(invitation_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/invitations/{invitation_id}")
def get_invitation(
    invitation_id: str,
    service: InvitationService = Depends(get_invitation_service),
):
    """Get invitation by ID."""
    try:
        return service.get_invitation_by_id(invitation_id)
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation not found")


@app.get("/invitations/code/{code}")
def get_invitation_by_code(
    code: str,
    service: InvitationService = Depends(get_invitation_service),
):
    """Get invitation by code."""
    try:
        return service.get_invitation_by_code(code)
    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation not found")


@app.post("/invitations/validate")
def validate_invitation(
    code: str,
    service: InvitationService = Depends(get_invitation_service),
):
    """Validate an invitation code."""
    validation_request = ValidateInvitationRequest(code=code)
    return service.validate_invitation(validation_request)


@app.post("/invitations/use")
def use_invitation(
    request: UseInvitationAPIRequest,
    service: InvitationService = Depends(get_invitation_service),
):
    """Use an invitation code."""
    try:
        use_request = UseInvitationRequest(
            code=request.code,
            used_by=request.used_by,
        )
        return service.use_invitation(use_request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/invitations/creator/{user_id}")
def get_invitations_by_creator(
    user_id: str,
    service: InvitationService = Depends(get_invitation_service),
):
    """Get all invitations created by a user."""
    return service.get_invitations_by_creator(user_id)


@app.get("/invitations/stats")
def get_stats(service: InvitationService = Depends(get_invitation_service)):
    """Get invitation statistics."""
    return service.get_invitation_stats()


@app.get("/")
def root():
    """Root endpoint with API info."""
    return {
        "message": "Invitation API",
        "version": "1.0.0",
        "endpoints": {
            "POST /invitations": "Create a new invitation",
            "GET /invitations/{id}": "Get invitation by ID",
            "GET /invitations/code/{code}": "Get invitation by code",
            "POST /invitations/validate": "Validate invitation code",
            "POST /invitations/use": "Use invitation code",
            "GET /invitations/creator/{user_id}": "Get invitations by creator",
            "GET /invitations/stats": "Get statistics",
        },
    }


# Example usage in registration endpoint
@app.post("/auth/register")
def register_user(
    email: str,
    password: str,
    invitation_code: str,
    service: InvitationService = Depends(get_invitation_service),
):
    """Register a new user with an invitation code."""
    try:
        # Validate invitation
        validation = service.validate_invitation(ValidateInvitationRequest(code=invitation_code))

        if not validation.is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid invitation: {validation.reason}")

        # Use the invitation
        usage = service.use_invitation(
            UseInvitationRequest(code=invitation_code, used_by=email)
        )

        # TODO: Create user account here
        # user = create_user_account(email, password)

        return {
            "message": "User registered successfully",
            "email": email,
            "invitation_used": usage.code,
            "remaining_uses": usage.remaining_uses,
        }

    except InvitationNotFoundError:
        raise HTTPException(status_code=404, detail="Invitation not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
