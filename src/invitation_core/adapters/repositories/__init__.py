"""Repository adapters for invitation core."""

from invitation_core.adapters.repositories.memory import (
    InMemoryInvitationRepository,
)

__all__ = ["InMemoryInvitationRepository"]

# Optional adapters - only import if dependencies are installed
try:
    from invitation_core.adapters.repositories.sqlalchemy import (
        SQLAlchemyInvitationRepository,
        create_tables,
    )

    __all__.extend(["SQLAlchemyInvitationRepository", "create_tables"])
except ImportError:
    pass

try:
    from invitation_core.adapters.repositories.mongodb import (
        MongoDBInvitationRepository,
    )

    __all__.append("MongoDBInvitationRepository")
except ImportError:
    pass
