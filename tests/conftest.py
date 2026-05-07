"""Test fixtures and configuration for WhoDis."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["ADMIN_USERNAME"] = "testadmin"
os.environ["ADMIN_PASSWORD"] = "testpass123"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()

from whodis.auth import get_password_hash
from whodis.main import app
from whodis.models import Base, get_db


# Create test database engine
def get_test_engine():
    """Create a test database engine."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    engine = get_test_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    testing_session_local = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Create default admin user
    from whodis.models import User

    admin = User(
        username="testadmin",
        hashed_password=get_password_hash("testpass123"),
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client):
    """Create an authenticated test client."""
    # Login
    response = client.post(
        "/auth/login",
        data={"username": "testadmin", "password": "testpass123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    yield client


@pytest.fixture(scope="function")
def api_key(auth_client, db_session):
    """Create an API key for testing."""
    from whodis.auth import hash_api_key
    from whodis.models import APIKey

    key = "whodis_test_key_12345"
    key_hash = hash_api_key(key)

    api_key = APIKey(
        key_hash=key_hash,
        name="Test Key",
        created_by=1,
        is_active=True,
    )
    db_session.add(api_key)
    db_session.commit()

    return key


@pytest.fixture(scope="function")
def sample_person(auth_client, db_session):
    """Create a sample person for testing."""
    from whodis.models import Person

    person = Person(name="Test Person", notes="Test notes")
    db_session.add(person)
    db_session.commit()
    db_session.refresh(person)

    return person


@pytest.fixture(scope="function")
def sample_image():
    """Create a sample test image."""
    import io

    from PIL import Image

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    return img_bytes.getvalue()
