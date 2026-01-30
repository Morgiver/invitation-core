"""MongoDB repository implementation for invitations."""

import logging
from datetime import datetime
from typing import Optional

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from invitation_core.domain.exceptions import InvitationAlreadyExistsError
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode, UsageLimit
from invitation_core.interfaces.repository import IInvitationRepository

logger = logging.getLogger(__name__)


class MongoDBInvitationRepository(IInvitationRepository):
    """MongoDB implementation of invitation repository."""

    def __init__(self, database: Database, collection_name: str = "invitations") -> None:
        """Initialize repository with MongoDB database.

        Args:
            database: PyMongo database instance
            collection_name: Name of the collection (default: "invitations")
        """
        self.collection: Collection = database[collection_name]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self.collection.create_index("code", unique=True)
        self.collection.create_index("status")
        self.collection.create_index("created_by")
        self.collection.create_index("created_at")
        self.collection.create_index("expires_at")
        logger.debug("Ensured MongoDB indexes for invitations collection")

    @staticmethod
    def _to_domain(doc: dict) -> Invitation:
        """Convert MongoDB document to domain entity.

        Args:
            doc: MongoDB document

        Returns:
            Domain invitation entity
        """
        return Invitation(
            id=doc["id"],
            code=InvitationCode(doc["code"]),
            status=InvitationStatus(doc["status"]),
            created_by=doc["created_by"],
            created_at=doc["created_at"],
            expires_at=doc.get("expires_at"),
            usage_limit=UsageLimit(doc.get("usage_limit")),
            usage_count=doc.get("usage_count", 0),
            used_by=doc.get("used_by", []),
            metadata=doc.get("metadata", {}),
            revoked_at=doc.get("revoked_at"),
            revoked_by=doc.get("revoked_by"),
            revocation_reason=doc.get("revocation_reason"),
        )

    @staticmethod
    def _to_document(invitation: Invitation) -> dict:
        """Convert domain entity to MongoDB document.

        Args:
            invitation: Domain invitation entity

        Returns:
            MongoDB document
        """
        return {
            "id": invitation.id,
            "code": str(invitation.code).upper(),  # Store uppercase for case-insensitive search
            "status": invitation.status.value,
            "created_by": invitation.created_by,
            "created_at": invitation.created_at,
            "expires_at": invitation.expires_at,
            "usage_limit": invitation.usage_limit.value,
            "usage_count": invitation.usage_count,
            "used_by": invitation.used_by,
            "metadata": invitation.metadata,
            "revoked_at": invitation.revoked_at,
            "revoked_by": invitation.revoked_by,
            "revocation_reason": invitation.revocation_reason,
        }

    def save(self, invitation: Invitation) -> Invitation:
        """Save an invitation (create or update)."""
        doc = self._to_document(invitation)

        # Check if exists
        existing = self.collection.find_one({"id": invitation.id})

        if existing:
            # Update
            self.collection.update_one({"id": invitation.id}, {"$set": doc})
            logger.debug(f"Updated invitation {invitation.id}")
        else:
            # Check if code exists (different ID)
            code_exists = self.collection.find_one({"code": str(invitation.code).upper()})
            if code_exists:
                raise InvitationAlreadyExistsError(
                    f"Invitation code '{invitation.code}' already exists"
                )

            # Create
            self.collection.insert_one(doc)
            logger.debug(f"Created invitation {invitation.id}")

        return invitation

    def find_by_id(self, invitation_id: str) -> Optional[Invitation]:
        """Find an invitation by its ID."""
        doc = self.collection.find_one({"id": invitation_id})
        return self._to_domain(doc) if doc else None

    def find_by_code(self, code: InvitationCode) -> Optional[Invitation]:
        """Find an invitation by its code (case-insensitive)."""
        doc = self.collection.find_one({"code": str(code).upper()})
        return self._to_domain(doc) if doc else None

    def exists_by_code(self, code: InvitationCode) -> bool:
        """Check if an invitation exists with the given code."""
        return self.collection.find_one({"code": str(code).upper()}) is not None

    def find_by_created_by(self, user_id: str) -> list[Invitation]:
        """Find all invitations created by a user."""
        docs = self.collection.find({"created_by": user_id}).sort("created_at", -1)
        return [self._to_domain(doc) for doc in docs]

    def find_by_status(self, status: InvitationStatus) -> list[Invitation]:
        """Find all invitations with a given status."""
        docs = self.collection.find({"status": status.value}).sort("created_at", -1)
        return [self._to_domain(doc) for doc in docs]

    def find_expired(self, check_time: Optional[datetime] = None) -> list[Invitation]:
        """Find all expired invitations."""
        check_time = check_time or datetime.utcnow()
        docs = self.collection.find(
            {"expires_at": {"$ne": None, "$lte": check_time}}
        ).sort("expires_at", -1)
        return [self._to_domain(doc) for doc in docs]

    def delete(self, invitation_id: str) -> bool:
        """Delete an invitation."""
        result = self.collection.delete_one({"id": invitation_id})

        if result.deleted_count > 0:
            logger.info(f"Deleted invitation {invitation_id}")
            return True

        return False

    def count_by_status(self, status: InvitationStatus) -> int:
        """Count invitations by status."""
        return self.collection.count_documents({"status": status.value})
