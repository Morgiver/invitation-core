"""SQLAlchemy repository implementation for invitations."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from invitation_core.domain.exceptions import InvitationAlreadyExistsError
from invitation_core.domain.models import Invitation, InvitationStatus
from invitation_core.domain.value_objects import InvitationCode, UsageLimit
from invitation_core.interfaces.repository import IInvitationRepository

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class InvitationModel(Base):
    """SQLAlchemy model for invitations."""

    __tablename__ = "invitations"

    id = Column(String(36), primary_key=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    created_by = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    usage_limit = Column(Integer, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    used_by = Column(JSON, nullable=False, default=list)
    metadata = Column(JSON, nullable=False, default=dict)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(255), nullable=True)
    revocation_reason = Column(Text, nullable=True)


class SQLAlchemyInvitationRepository(IInvitationRepository):
    """SQLAlchemy implementation of invitation repository."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session
        """
        self.session = session

    @staticmethod
    def _to_domain(model: InvitationModel) -> Invitation:
        """Convert SQLAlchemy model to domain entity.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain invitation entity
        """
        return Invitation(
            id=model.id,
            code=InvitationCode(model.code),
            status=InvitationStatus(model.status),
            created_by=model.created_by,
            created_at=model.created_at,
            expires_at=model.expires_at,
            usage_limit=UsageLimit(model.usage_limit),
            usage_count=model.usage_count,
            used_by=model.used_by or [],
            metadata=model.metadata or {},
            revoked_at=model.revoked_at,
            revoked_by=model.revoked_by,
            revocation_reason=model.revocation_reason,
        )

    @staticmethod
    def _to_model(invitation: Invitation) -> InvitationModel:
        """Convert domain entity to SQLAlchemy model.

        Args:
            invitation: Domain invitation entity

        Returns:
            SQLAlchemy model
        """
        return InvitationModel(
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

    def save(self, invitation: Invitation) -> Invitation:
        """Save an invitation (create or update)."""
        # Check if exists (for create)
        existing = (
            self.session.query(InvitationModel).filter_by(id=invitation.id).first()
        )

        if existing:
            # Update
            existing.code = str(invitation.code)
            existing.status = invitation.status.value
            existing.expires_at = invitation.expires_at
            existing.usage_limit = invitation.usage_limit.value
            existing.usage_count = invitation.usage_count
            existing.used_by = invitation.used_by
            existing.metadata = invitation.metadata
            existing.revoked_at = invitation.revoked_at
            existing.revoked_by = invitation.revoked_by
            existing.revocation_reason = invitation.revocation_reason
            logger.debug(f"Updated invitation {invitation.id}")
        else:
            # Check if code exists (different ID)
            code_exists = (
                self.session.query(InvitationModel)
                .filter_by(code=str(invitation.code))
                .first()
            )
            if code_exists:
                raise InvitationAlreadyExistsError(
                    f"Invitation code '{invitation.code}' already exists"
                )

            # Create
            model = self._to_model(invitation)
            self.session.add(model)
            logger.debug(f"Created invitation {invitation.id}")

        self.session.commit()
        return invitation

    def find_by_id(self, invitation_id: str) -> Optional[Invitation]:
        """Find an invitation by its ID."""
        model = (
            self.session.query(InvitationModel).filter_by(id=invitation_id).first()
        )
        return self._to_domain(model) if model else None

    def find_by_code(self, code: InvitationCode) -> Optional[Invitation]:
        """Find an invitation by its code."""
        model = (
            self.session.query(InvitationModel)
            .filter(InvitationModel.code.ilike(str(code)))
            .first()
        )
        return self._to_domain(model) if model else None

    def exists_by_code(self, code: InvitationCode) -> bool:
        """Check if an invitation exists with the given code."""
        return (
            self.session.query(InvitationModel)
            .filter(InvitationModel.code.ilike(str(code)))
            .first()
            is not None
        )

    def find_by_created_by(self, user_id: str) -> list[Invitation]:
        """Find all invitations created by a user."""
        models = (
            self.session.query(InvitationModel)
            .filter_by(created_by=user_id)
            .order_by(InvitationModel.created_at.desc())
            .all()
        )
        return [self._to_domain(model) for model in models]

    def find_by_status(self, status: InvitationStatus) -> list[Invitation]:
        """Find all invitations with a given status."""
        models = (
            self.session.query(InvitationModel)
            .filter_by(status=status.value)
            .order_by(InvitationModel.created_at.desc())
            .all()
        )
        return [self._to_domain(model) for model in models]

    def find_expired(self, check_time: Optional[datetime] = None) -> list[Invitation]:
        """Find all expired invitations."""
        check_time = check_time or datetime.utcnow()
        models = (
            self.session.query(InvitationModel)
            .filter(
                InvitationModel.expires_at.isnot(None),
                InvitationModel.expires_at <= check_time,
            )
            .order_by(InvitationModel.expires_at.desc())
            .all()
        )
        return [self._to_domain(model) for model in models]

    def delete(self, invitation_id: str) -> bool:
        """Delete an invitation."""
        model = (
            self.session.query(InvitationModel).filter_by(id=invitation_id).first()
        )

        if not model:
            return False

        self.session.delete(model)
        self.session.commit()
        logger.info(f"Deleted invitation {invitation_id}")
        return True

    def count_by_status(self, status: InvitationStatus) -> int:
        """Count invitations by status."""
        return (
            self.session.query(InvitationModel).filter_by(status=status.value).count()
        )


def create_tables(engine) -> None:
    """Create all tables in the database.

    Args:
        engine: SQLAlchemy engine
    """
    Base.metadata.create_all(engine)
    logger.info("Created invitation tables")
