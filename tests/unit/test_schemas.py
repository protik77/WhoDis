"""Unit tests for Pydantic schemas."""

from datetime import datetime

from whodis.schemas import (
    PersonCreate,
    PersonResponse,
    DetectionResponse,
    APIKeyCreate,
    LoginRequest,
)


class TestPersonCreate:
    """Test PersonCreate schema."""

    def test_valid_person_create(self):
        """Test creating a valid person."""
        person = PersonCreate(name="John Doe", notes="Some notes")

        assert person.name == "John Doe"
        assert person.notes == "Some notes"

    def test_person_create_no_notes(self):
        """Test creating a person without notes."""
        person = PersonCreate(name="Jane Doe")

        assert person.name == "Jane Doe"
        assert person.notes is None


class TestDetectionResponse:
    """Test DetectionResponse schema."""

    def test_detection_with_match(self):
        """Test response with a match."""
        response = DetectionResponse(
            person="John Doe",
            person_id=1,
            confidence=0.95,
            queued_for_annotation=False,
            engine_used="imagehash",
        )

        assert response.person == "John Doe"
        assert response.confidence == 0.95
        assert response.queued_for_annotation is False

    def test_detection_no_match(self):
        """Test response without a match."""
        response = DetectionResponse(
            person=None,
            person_id=None,
            confidence=0.0,
            queued_for_annotation=True,
            engine_used="imagehash",
        )

        assert response.person is None
        assert response.queued_for_annotation is True

    def test_confidence_range(self):
        """Test confidence must be between 0 and 1."""
        from pydantic import ValidationError

        try:
            DetectionResponse(
                person="Test",
                confidence=1.5,  # Invalid: > 1
                engine_used="imagehash",
            )
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass


class TestAPIKeyCreate:
    """Test APIKeyCreate schema."""

    def test_with_name(self):
        """Test creating API key with name."""
        data = APIKeyCreate(name="Test Key")

        assert data.name == "Test Key"

    def test_without_name(self):
        """Test creating API key without name."""
        data = APIKeyCreate()

        assert data.name is None


class TestLoginRequest:
    """Test LoginRequest schema."""

    def test_valid_login(self):
        """Test valid login request."""
        login = LoginRequest(username="admin", password="secret")

        assert login.username == "admin"
        assert login.password == "secret"
