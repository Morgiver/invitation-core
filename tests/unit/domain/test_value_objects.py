"""Unit tests for domain value objects."""

import pytest

from invitation_core.domain.exceptions import InvalidInvitationCodeError
from invitation_core.domain.value_objects import InvitationCode, UsageLimit


class TestInvitationCode:
    """Tests for InvitationCode value object."""

    def test_valid_code_creation(self) -> None:
        """Test creating a valid invitation code."""
        code = InvitationCode("WELCOME2024")
        assert code.value == "WELCOME2024"

    def test_code_with_hyphens(self) -> None:
        """Test code can contain hyphens."""
        code = InvitationCode("WELCOME-2024")
        assert code.value == "WELCOME-2024"

    def test_code_with_underscores(self) -> None:
        """Test code can contain underscores."""
        code = InvitationCode("WELCOME_2024")
        assert code.value == "WELCOME_2024"

    def test_code_too_short_raises_error(self) -> None:
        """Test that codes shorter than 6 characters raise an error."""
        with pytest.raises(InvalidInvitationCodeError, match="at least 6 characters"):
            InvitationCode("HELLO")

    def test_code_too_long_raises_error(self) -> None:
        """Test that codes longer than 32 characters raise an error."""
        with pytest.raises(InvalidInvitationCodeError, match="at most 32 characters"):
            InvitationCode("A" * 33)

    def test_empty_code_raises_error(self) -> None:
        """Test that empty codes raise an error."""
        with pytest.raises(InvalidInvitationCodeError, match="cannot be empty"):
            InvitationCode("")

    def test_code_with_special_characters_raises_error(self) -> None:
        """Test that codes with special characters raise an error."""
        with pytest.raises(InvalidInvitationCodeError, match="alphanumeric"):
            InvitationCode("HELLO@2024")

    def test_code_with_spaces_raises_error(self) -> None:
        """Test that codes with spaces raise an error."""
        with pytest.raises(InvalidInvitationCodeError, match="alphanumeric"):
            InvitationCode("HELLO 2024")

    def test_code_equality_case_insensitive(self) -> None:
        """Test that code comparison is case-insensitive."""
        code1 = InvitationCode("WELCOME2024")
        code2 = InvitationCode("welcome2024")
        assert code1 == code2

    def test_code_string_representation(self) -> None:
        """Test that string representation is uppercase."""
        code = InvitationCode("welcome2024")
        assert str(code) == "WELCOME2024"

    def test_code_hash_case_insensitive(self) -> None:
        """Test that hash is case-insensitive."""
        code1 = InvitationCode("WELCOME2024")
        code2 = InvitationCode("welcome2024")
        assert hash(code1) == hash(code2)


class TestUsageLimit:
    """Tests for UsageLimit value object."""

    def test_valid_limit_creation(self) -> None:
        """Test creating a valid usage limit."""
        limit = UsageLimit(5)
        assert limit.value == 5

    def test_unlimited_creation(self) -> None:
        """Test creating an unlimited usage limit."""
        limit = UsageLimit(None)
        assert limit.value is None

    def test_zero_limit(self) -> None:
        """Test that zero is a valid limit."""
        limit = UsageLimit(0)
        assert limit.value == 0

    def test_negative_limit_raises_error(self) -> None:
        """Test that negative limits raise an error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            UsageLimit(-1)

    def test_is_unlimited(self) -> None:
        """Test is_unlimited method."""
        assert UsageLimit(None).is_unlimited() is True
        assert UsageLimit(5).is_unlimited() is False

    def test_is_reached_with_limit(self) -> None:
        """Test is_reached method with a limit."""
        limit = UsageLimit(3)
        assert limit.is_reached(2) is False
        assert limit.is_reached(3) is True
        assert limit.is_reached(4) is True

    def test_is_reached_unlimited(self) -> None:
        """Test that unlimited limits are never reached."""
        limit = UsageLimit(None)
        assert limit.is_reached(0) is False
        assert limit.is_reached(100) is False
        assert limit.is_reached(999999) is False

    def test_string_representation(self) -> None:
        """Test string representation."""
        assert str(UsageLimit(5)) == "5"
        assert str(UsageLimit(None)) == "unlimited"
