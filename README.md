# Invitation Core

A domain-focused, framework-agnostic Python package for managing invitation codes following **Hexagonal Architecture** and **Domain-Driven Design** principles.

## Features

- **Framework-agnostic**: Use with FastAPI, Flask, Django, or any Python framework
- **Multiple storage backends**: SQLAlchemy (PostgreSQL, MySQL, SQLite), MongoDB, or in-memory
- **Flexible invitation types**: Single-use, multi-use, or unlimited invitations
- **Expiration support**: Set optional expiration dates
- **Event-driven**: Publishes domain events for integration with other systems
- **Type-safe**: Full type hints and Pydantic validation
- **Well-tested**: Comprehensive unit and integration tests

## Installation

### Basic installation (in-memory storage only)
```bash
pip install invitation-core
```

### With SQLAlchemy support
```bash
pip install invitation-core[sqlalchemy]
```

### With MongoDB support
```bash
pip install invitation-core[mongodb]
```

### Install all optional dependencies
```bash
pip install invitation-core[all]
```

## Quick Start

### Basic Usage (In-Memory)

```python
from invitation_core import (
    InvitationService,
    CreateInvitationRequest,
    UseInvitationRequest,
)
from invitation_core.adapters import InMemoryInvitationRepository, InMemoryEventBus

# Set up repository and service
repository = InMemoryInvitationRepository()
event_bus = InMemoryEventBus()
service = InvitationService(repository, event_bus)

# Create an invitation
request = CreateInvitationRequest(
    code="WELCOME2024",
    created_by="admin@example.com",
    usage_limit=5,  # Can be used 5 times
    metadata={"campaign": "winter_2024"}
)
invitation = service.create_invitation(request)
print(f"Created invitation: {invitation.code}")

# Validate an invitation
validation = service.validate_invitation(
    ValidateInvitationRequest(code="WELCOME2024")
)
if validation.is_valid:
    print(f"Invitation is valid! {validation.remaining_uses} uses remaining")

# Use an invitation
usage = service.use_invitation(
    UseInvitationRequest(
        code="WELCOME2024",
        used_by="user@example.com"
    )
)
print(f"Invitation used! {usage.remaining_uses} uses remaining")
```

### With SQLAlchemy (PostgreSQL)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from invitation_core import InvitationService
from invitation_core.adapters.repositories.sqlalchemy import (
    SQLAlchemyInvitationRepository,
    create_tables,
)

# Set up database
engine = create_engine("postgresql://user:password@localhost:5432/mydb")
create_tables(engine)  # Create tables

Session = sessionmaker(bind=engine)
session = Session()

# Create service
repository = SQLAlchemyInvitationRepository(session)
service = InvitationService(repository)

# Use the service as shown above
```

### With MongoDB

```python
from pymongo import MongoClient
from invitation_core import InvitationService
from invitation_core.adapters.repositories.mongodb import (
    MongoDBInvitationRepository,
)

# Set up MongoDB
client = MongoClient("mongodb://localhost:27017/")
database = client["mydb"]

# Create service
repository = MongoDBInvitationRepository(database)
service = InvitationService(repository)

# Use the service as shown above
```

## Key Concepts

### Invitation Types

**Single-use** (default):
```python
CreateInvitationRequest(
    code="SINGLE123",
    created_by="admin",
    usage_limit=1
)
```

**Multi-use**:
```python
CreateInvitationRequest(
    code="MULTI123",
    created_by="admin",
    usage_limit=10  # Can be used 10 times
)
```

**Unlimited**:
```python
CreateInvitationRequest(
    code="UNLIMITED",
    created_by="admin",
    usage_limit=None  # No limit
)
```

### Expiration

```python
from datetime import datetime, timedelta

CreateInvitationRequest(
    code="EXPIRES123",
    created_by="admin",
    expires_at=datetime.utcnow() + timedelta(days=30)
)
```

### Domain Events

The service publishes the following events:
- `InvitationCreatedEvent` - When an invitation is created
- `InvitationUsedEvent` - When an invitation is used
- `InvitationRevokedEvent` - When an invitation is revoked
- `InvitationExpiredEvent` - When an invitation expires
- `InvitationLimitReachedEvent` - When usage limit is reached

Subscribe to events:
```python
from invitation_core.adapters import InMemoryEventBus
from invitation_core.events import InvitationUsedEvent

event_bus = InMemoryEventBus()

def on_invitation_used(event: InvitationUsedEvent):
    print(f"Invitation {event.code} used by {event.used_by}")
    # Send welcome email, grant access, etc.

event_bus.subscribe(InvitationUsedEvent, on_invitation_used)
```

## Use Cases

### User Registration with Invitations

```python
from invitation_core import InvitationService, UseInvitationRequest
from invitation_core.domain.exceptions import (
    InvitationExpiredError,
    InvitationNotFoundError,
)

def register_user(email: str, invitation_code: str, invitation_service: InvitationService):
    try:
        # Validate and use invitation
        usage = invitation_service.use_invitation(
            UseInvitationRequest(code=invitation_code, used_by=email)
        )

        # Create user account
        user = create_user(email)

        # Grant special benefits based on metadata
        invitation = invitation_service.get_invitation_by_code(invitation_code)
        if invitation.metadata.get("premium"):
            grant_premium_access(user)

        return user

    except InvitationNotFoundError:
        raise ValueError("Invalid invitation code")
    except InvitationExpiredError:
        raise ValueError("Invitation has expired")
```

### Referral System

```python
from datetime import datetime, timedelta
from invitation_core import CreateInvitationRequest

def create_referral_code(user_id: str, service: InvitationService):
    """Generate a unique referral code for a user."""
    code = f"REF-{user_id[:8].upper()}"

    invitation = service.create_invitation(
        CreateInvitationRequest(
            code=code,
            created_by=user_id,
            usage_limit=None,  # Unlimited uses
            expires_at=datetime.utcnow() + timedelta(days=365),
            metadata={"type": "referral", "referrer_id": user_id}
        )
    )

    return invitation.code

def get_referral_stats(user_id: str, service: InvitationService):
    """Get referral statistics for a user."""
    invitations = service.get_invitations_by_creator(user_id)

    total_uses = sum(inv.usage_count for inv in invitations)
    active_codes = sum(1 for inv in invitations if inv.status == "active")

    return {
        "total_referrals": total_uses,
        "active_codes": active_codes,
        "invitations": invitations
    }
```

## Architecture

This package follows **Hexagonal Architecture**:

```
[Domain Layer]         - Pure business logic (no dependencies)
    |
[Interfaces]           - Abstract contracts
    |
[Adapters]            - Concrete implementations (SQLAlchemy, MongoDB, etc.)
    |
[Your Application]    - FastAPI, Flask, Django, etc.
```

### Dependency Injection

You provide the implementations:

```python
# Your choice of repository
repository = SQLAlchemyInvitationRepository(session)
# or: repository = MongoDBInvitationRepository(database)
# or: repository = InMemoryInvitationRepository()

# Your choice of event bus
event_bus = InMemoryEventBus()
# or: event_bus = RedisEventBus(redis_client)
# or: event_bus = None  # No events

# Wire them together
service = InvitationService(repository, event_bus)
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev,test]"

# Run unit tests only (no database required)
pytest tests/unit tests/contracts

# Run with coverage
pytest tests/unit tests/contracts --cov=src/invitation_core --cov-report=html
```

### Integration Tests with Real Databases

To run integration tests with PostgreSQL or MongoDB:

```bash
# Setup PostgreSQL test database
python scripts/setup_test_db.py \
  --db-type postgresql \
  --host localhost \
  --username postgres \
  --password yourpassword \
  --db-name test_invitation_core

# Set environment variable
export TEST_DB_CONNECTION_STRING="postgresql://postgres:yourpassword@localhost:5432/test_invitation_core"

# Run PostgreSQL integration tests
pytest tests/integration/test_sqlalchemy_repository.py
```

```bash
# Setup MongoDB test database
python scripts/setup_test_db.py \
  --db-type mongodb \
  --host localhost \
  --username admin \
  --password yourpassword \
  --db-name test_invitation_core

# Set environment variables
export TEST_MONGO_CONNECTION_STRING="mongodb://admin:yourpassword@localhost:27017/"
export TEST_MONGO_DB_NAME="test_invitation_core"

# Run MongoDB integration tests
pytest tests/integration/test_mongodb_repository.py
```

```bash
# Run ALL tests (unit + integration)
pytest
```

## Examples

See the [examples/](examples/) directory for complete examples:
- [Basic usage](examples/01_basic_example.py)
- [FastAPI integration](examples/02_fastapi_example.py)
- [Event-driven integration](examples/03_event_driven_example.py)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
