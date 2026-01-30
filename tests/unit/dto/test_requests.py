"""Unit tests for request DTOs."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from invitation_core.dto.requests import (
    CreateInvitationRequest,
    RevokeInvitationRequest,
    UseInvitationRequest,
    ValidateInvitationRequest,
)


class TestCreateInvitationRequest:
    """Tests for CreateInvitationRequest DTO."""

    def test_valid_request(self):
        """Test creating valid request."""
        request = CreateInvitationRequest(
            code="VALID123",
            created_by="user@example.com",
            usage_limit=5,
            metadata={"source": "campaign"},
        )

        assert request.code == "VALID123"
        assert request.created_by == "user@example.com"
        assert request.usage_limit == 5
        assert request.metadata == {"source": "campaign"}

    def test_minimal_request(self):
        """Test creating request with minimal fields."""
        request = CreateInvitationRequest(
            code="MINIMAL",
            created_by="user",
        )

        assert request.code == "MINIMAL"
        assert request.created_by == "user"
        assert request.expires_at is None
        assert request.usage_limit == 1  # Default
        assert request.metadata == {}  # Default

    def test_code_too_short_raises_error(self):
        """Test that code shorter than 6 characters raises error."""
        with pytest.raises(ValidationError, match="at least 6 characters"):
            CreateInvitationRequest(
                code="SHORT",
                created_by="user",
            )

    def test_code_too_long_raises_error(self):
        """Test that code longer than 32 characters raises error."""
        with pytest.raises(ValidationError, match="at most 32 characters"):
            CreateInvitationRequest(
                code="A" * 33,
                created_by="user",
            )

    def test_code_with_special_characters_raises_error(self):
        """Test that code with special characters raises error."""
        with pytest.raises(ValidationError, match="alphanumeric"):
            CreateInvitationRequest(
                code="INVALID@CODE",
                created_by="user",
            )

    def test_code_with_spaces_raises_error(self):
        """Test that code with spaces raises error."""
        with pytest.raises(ValidationError, match="alphanumeric"):
            CreateInvitationRequest(
                code="INVALID CODE",
                created_by="user",
            )

    def test_code_with_hyphens_allowed(self):
        """Test that code with hyphens is allowed."""
        request = CreateInvitationRequest(
            code="CODE-WITH-HYPHENS",
            created_by="user",
        )
        assert request.code == "CODE-WITH-HYPHENS"

    def test_code_with_underscores_allowed(self):
        """Test that code with underscores is allowed."""
        request = CreateInvitationRequest(
            code="CODE_WITH_UNDERSCORES",
            created_by="user",
        )
        assert request.code == "CODE_WITH_UNDERSCORES"

    def test_empty_created_by_raises_error(self):
        """Test that empty created_by raises error."""
        with pytest.raises(ValidationError):
            CreateInvitationRequest(
                code="VALID123",
                created_by="",
            )

    def test_past_expiration_raises_error(self):
        """Test that past expiration date raises error."""
        past = datetime.utcnow() - timedelta(days=1)
        with pytest.raises(ValidationError, match="must be in the future"):
            CreateInvitationRequest(
                code="EXPIRED",
                created_by="user",
                expires_at=past,
            )

    def test_future_expiration_valid(self):
        """Test that future expiration date is valid."""
        future = datetime.utcnow() + timedelta(days=7)
        request = CreateInvitationRequest(
            code="FUTURE",
            created_by="user",
            expires_at=future,
        )
        assert request.expires_at == future

    def test_usage_limit_zero_raises_error(self):
        """Test that usage limit of 0 raises error."""
        with pytest.raises(ValidationError, match="greater than or equal to 1"):
            CreateInvitationRequest(
                code="ZERO",
                created_by="user",
                usage_limit=0,
            )

    def test_usage_limit_negative_raises_error(self):
        """Test that negative usage limit raises error."""
        with pytest.raises(ValidationError):
            CreateInvitationRequest(
                code="NEGATIVE",
                created_by="user",
                usage_limit=-1,
            )

    def test_usage_limit_none_for_unlimited(self):
        """Test that None usage limit is valid (unlimited)."""
        request = CreateInvitationRequest(
            code="UNLIMITED",
            created_by="user",
            usage_limit=None,
        )
        assert request.usage_limit is None


class TestUseInvitationRequest:
    """Tests for UseInvitationRequest DTO."""

    def test_valid_request(self):
        """Test creating valid request."""
        request = UseInvitationRequest(
            code="USE123",
            used_by="user@example.com",
        )

        assert request.code == "USE123"
        assert request.used_by == "user@example.com"

    def test_code_too_short_raises_error(self):
        """Test that code shorter than 6 characters raises error."""
        with pytest.raises(ValidationError):
            UseInvitationRequest(
                code="SHORT",
                used_by="user@example.com",
            )

    def test_empty_used_by_raises_error(self):
        """Test that empty used_by raises error."""
        with pytest.raises(ValidationError):
            UseInvitationRequest(
                code="VALID123",
                used_by="",
            )


class TestRevokeInvitationRequest:
    """Tests for RevokeInvitationRequest DTO."""

    def test_valid_request(self):
        """Test creating valid request."""
        request = RevokeInvitationRequest(
            invitation_id="123e4567-e89b-12d3-a456-426614174000",
            revoked_by="admin@example.com",
            reason="Violation of terms",
        )

        assert request.invitation_id == "123e4567-e89b-12d3-a456-426614174000"
        assert request.revoked_by == "admin@example.com"
        assert request.reason == "Violation of terms"

    def test_request_without_reason(self):
        """Test creating request without reason."""
        request = RevokeInvitationRequest(
            invitation_id="123",
            revoked_by="admin",
        )

        assert request.invitation_id == "123"
        assert request.reason is None

    def test_empty_invitation_id_raises_error(self):
        """Test that empty invitation_id raises error."""
        with pytest.raises(ValidationError):
            RevokeInvitationRequest(
                invitation_id="",
                revoked_by="admin",
            )

    def test_empty_revoked_by_raises_error(self):
        """Test that empty revoked_by raises error."""
        with pytest.raises(ValidationError):
            RevokeInvitationRequest(
                invitation_id="123",
                revoked_by="",
            )

    def test_reason_too_long_raises_error(self):
        """Test that reason longer than 500 characters raises error."""
        with pytest.raises(ValidationError):
            RevokeInvitationRequest(
                invitation_id="123",
                revoked_by="admin",
                reason="A" * 501,
            )


class TestValidateInvitationRequest:
    """Tests for ValidateInvitationRequest DTO."""

    def test_valid_request(self):
        """Test creating valid request."""
        request = ValidateInvitationRequest(code="VALIDATE")

        assert request.code == "VALIDATE"

    def test_code_too_short_raises_error(self):
        """Test that code shorter than 6 characters raises error."""
        with pytest.raises(ValidationError):
            ValidateInvitationRequest(code="SHORT")

    def test_code_too_long_raises_error(self):
        """Test that code longer than 32 characters raises error."""
        with pytest.raises(ValidationError):
            ValidateInvitationRequest(code="A" * 33)
