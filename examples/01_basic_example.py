"""Basic example of using invitation-core.

This example demonstrates:
- Creating invitations
- Validating invitations
- Using invitations
- Revoking invitations
- Getting statistics
"""

from datetime import datetime, timedelta

from invitation_core import (
    CreateInvitationRequest,
    InvitationService,
    RevokeInvitationRequest,
    UseInvitationRequest,
    ValidateInvitationRequest,
)
from invitation_core.adapters import InMemoryEventBus, InMemoryInvitationRepository
from invitation_core.domain.exceptions import (
    InvitationAlreadyUsedError,
    InvitationExpiredError,
    InvitationLimitReachedError,
)
from invitation_core.events import InvitationUsedEvent


def main():
    """Run the basic example."""
    print("=== Invitation Core - Basic Example ===\n")

    # Setup: Create repository and service
    repository = InMemoryInvitationRepository()
    event_bus = InMemoryEventBus()
    service = InvitationService(repository, event_bus)

    # Subscribe to events
    def on_invitation_used(event: InvitationUsedEvent):
        print(f"[EVENT] Invitation {event.code} used by {event.used_by}")
        print(f"        Usage: {event.usage_count}, Remaining: {event.remaining_uses}")

    event_bus.subscribe(InvitationUsedEvent, on_invitation_used)

    # 1. Create a single-use invitation
    print("1. Creating single-use invitation...")
    single_use = service.create_invitation(
        CreateInvitationRequest(
            code="WELCOME2024",
            created_by="admin@example.com",
            usage_limit=1,
            expires_at=datetime.utcnow() + timedelta(days=7),
            metadata={"campaign": "winter_2024", "discount": "20%"},
        )
    )
    print(f"   Created: {single_use.code} (ID: {single_use.id})")
    print(f"   Expires: {single_use.expires_at}")
    print()

    # 2. Create a multi-use invitation
    print("2. Creating multi-use invitation...")
    multi_use = service.create_invitation(
        CreateInvitationRequest(
            code="FRIEND5",
            created_by="admin@example.com",
            usage_limit=5,
            metadata={"type": "referral"},
        )
    )
    print(f"   Created: {multi_use.code} (5 uses allowed)")
    print()

    # 3. Create an unlimited invitation
    print("3. Creating unlimited invitation...")
    unlimited = service.create_invitation(
        CreateInvitationRequest(
            code="PARTNER-VIP",
            created_by="admin@example.com",
            usage_limit=None,
            expires_at=datetime.utcnow() + timedelta(days=365),
            metadata={"partner": "acme_corp", "tier": "vip"},
        )
    )
    print(f"   Created: {unlimited.code} (unlimited uses)")
    print()

    # 4. Validate an invitation
    print("4. Validating invitation...")
    validation = service.validate_invitation(ValidateInvitationRequest(code="FRIEND5"))
    print(f"   Code: {validation.code}")
    print(f"   Valid: {validation.is_valid}")
    print(f"   Status: {validation.status}")
    print(f"   Remaining uses: {validation.remaining_uses}")
    print()

    # 5. Use invitations
    print("5. Using invitations...")
    print("   a) Using FRIEND5 (multi-use)...")
    for i in range(1, 4):
        usage = service.use_invitation(
            UseInvitationRequest(code="FRIEND5", used_by=f"user{i}@example.com")
        )
        print(f"      Use {i}: {usage.used_by} - {usage.remaining_uses} remaining")
    print()

    print("   b) Using WELCOME2024 (single-use)...")
    usage = service.use_invitation(
        UseInvitationRequest(code="WELCOME2024", used_by="newuser@example.com")
    )
    print(f"      Used by: {usage.used_by}")
    print(f"      Is exhausted: {usage.is_exhausted}")
    print()

    # 6. Try to use an exhausted invitation
    print("6. Attempting to use exhausted invitation...")
    try:
        service.use_invitation(
            UseInvitationRequest(code="WELCOME2024", used_by="another@example.com")
        )
    except (InvitationLimitReachedError, InvitationAlreadyUsedError) as e:
        print(f"   [ERROR] {e}")
    print()

    # 7. Test expiration
    print("7. Testing expiration...")
    # Create invitation that expires in 1 second
    short_lived = service.create_invitation(
        CreateInvitationRequest(
            code="SHORTLIVED",
            created_by="admin@example.com",
            expires_at=datetime.utcnow() + timedelta(seconds=1),
        )
    )
    print(f"   Created short-lived invitation: {short_lived.code}")
    print("   Waiting for expiration...")
    import time
    time.sleep(2)

    try:
        service.use_invitation(UseInvitationRequest(code="SHORTLIVED", used_by="test@example.com"))
    except InvitationExpiredError as e:
        print(f"   [ERROR] {e}")
    print()

    # 8. Revoke an invitation
    print("8. Revoking an invitation...")
    invitation = service.get_invitation_by_code("FRIEND5")
    revoked = service.revoke_invitation(
        RevokeInvitationRequest(
            invitation_id=invitation.id,
            revoked_by="admin@example.com",
            reason="Promotion ended early",
        )
    )
    print(f"   Revoked: {revoked.code}")
    print(f"   Reason: {revoked.revocation_reason}")
    print()

    # 9. Get statistics
    print("9. Getting statistics...")
    stats = service.get_invitation_stats()
    print(f"   Total invitations: {stats.total}")
    print(f"   Active: {stats.active}")
    print(f"   Used: {stats.used}")
    print(f"   Expired: {stats.expired}")
    print(f"   Revoked: {stats.revoked}")
    print()

    # 10. Get invitations by creator
    print("10. Getting invitations by creator...")
    admin_invitations = service.get_invitations_by_creator("admin@example.com")
    print(f"    Admin has created {len(admin_invitations)} invitations:")
    for inv in admin_invitations:
        print(f"    - {inv.code}: {inv.status} ({inv.usage_count} uses)")
    print()

    print("=== Example Complete ===")


if __name__ == "__main__":
    main()
