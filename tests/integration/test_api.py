"""Integration tests for API endpoints."""

import io


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "whodis"


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "testpass123"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert "session" in response.cookies

    def test_login_failure(self, client):
        """Test failed login."""
        response = client.post(
            "/auth/login",
            data={"username": "testadmin", "password": "wrongpassword"},
        )

        assert response.status_code == 401

    def test_logout(self, auth_client):
        """Test logout clears session."""
        response = auth_client.get("/auth/logout", follow_redirects=False)

        assert response.status_code == 302

    def test_me_endpoint(self, auth_client):
        """Test getting current user info."""
        response = auth_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testadmin"
        assert data["is_admin"] is True


class TestAPIKeyEndpoints:
    """Test API key management endpoints."""

    def test_create_api_key(self, auth_client):
        """Test creating an API key."""
        response = auth_client.post(
            "/auth/api-keys",
            data={"name": "Test API Key"},
        )

        assert response.status_code == 200
        assert "Test API Key" in response.text

    def test_list_api_keys(self, auth_client, api_key):
        """Test listing API keys."""
        response = auth_client.get("/auth/api-keys")

        assert response.status_code == 200

    def test_revoke_api_key(self, auth_client, api_key, db_session):
        """Test revoking an API key."""
        from whodis.models import APIKey

        # Get the key ID
        key = db_session.query(APIKey).first()

        response = auth_client.post(
            f"/auth/api-keys/{key.id}/revoke", follow_redirects=False
        )

        assert response.status_code == 302


class TestWebEndpoints:
    """Test web interface endpoints."""

    def test_login_page(self, client):
        """Test login page loads."""
        response = client.get("/login")

        assert response.status_code == 200
        assert "Login" in response.text

    def test_dashboard_requires_auth_redirect(self, client):
        """Test dashboard redirects to login for HTML requests."""
        response = client.get(
            "/", headers={"Accept": "text/html"}, follow_redirects=False
        )

        assert response.status_code == 307
        assert response.headers["location"] == "/login"

    def test_dashboard_requires_auth_api(self, client):
        """Test dashboard still returns 401 for non-HTML requests."""
        response = client.get("/", headers={"Accept": "application/json"})

        assert response.status_code == 401

    def test_dashboard_authenticated(self, auth_client):
        """Test dashboard loads when authenticated."""
        response = auth_client.get("/", headers={"Accept": "text/html"})

        assert response.status_code == 200
        assert "Dashboard" in response.text

    def test_people_page(self, auth_client):
        """Test people page loads."""
        response = auth_client.get("/people")

        assert response.status_code == 200
        assert "People" in response.text

    def test_annotate_page(self, auth_client):
        """Test annotation page loads."""
        response = auth_client.get("/annotate")

        assert response.status_code == 200
        assert "Annotation" in response.text

    def test_submit_annotation_new_person(self, auth_client, db_session, sample_image):
        """Test submitting annotation form creates new person."""
        from whodis.models import AnnotationQueue, DetectionLog

        # Create a pending annotation first
        log = DetectionLog(
            image_path="test.jpg", confidence=0.0, engine_used="imagehash"
        )
        db_session.add(log)
        db_session.commit()

        queue_item = AnnotationQueue(
            detection_log_id=log.id, image_path="test.jpg", status="pending"
        )
        db_session.add(queue_item)
        db_session.commit()

        # Write a real test image file so PIL can open it
        from whodis.config import UPLOAD_DIR

        with open(UPLOAD_DIR / "test.jpg", "wb") as f:
            f.write(sample_image)

        response = auth_client.post(
            f"/annotate/{queue_item.id}",
            data={
                "new_person_name": "Test Person From Annotation",
                "person_id": "",
                "ignore": "false",
                "engine": "",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302

        # Verify it was annotated
        db_session.refresh(queue_item)
        assert queue_item.status == "annotated"
        assert queue_item.suggested_person.name == "Test Person From Annotation"


class TestDetectionAPI:
    """Test detection API endpoints."""

    def test_detect_requires_api_key(self, client):
        """Test detection requires API key."""
        response = client.post("/api/detect")

        assert response.status_code == 401

    def test_detect_with_invalid_key(self, client):
        """Test detection with invalid API key."""
        response = client.post(
            "/api/detect",
            headers={"Authorization": "Bearer invalid_key"},
        )

        assert response.status_code == 401

    def test_detect_with_valid_key(self, auth_client, api_key, sample_image):
        """Test detection with valid API key."""
        # Create a file-like object from sample image
        img_file = io.BytesIO(sample_image)

        response = auth_client.post(
            "/api/detect",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"image": ("test.jpg", img_file, "image/jpeg")},
        )

        # Should return 200 even if no match found
        assert response.status_code in [200, 422]

    def test_list_engines(self, auth_client, api_key):
        """Test listing available engines."""
        response = auth_client.get(
            "/api/engines",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "engines" in data
        assert "imagehash" in data["engines"]


class TestPersonManagement:
    """Test person management endpoints."""

    def test_create_person(self, auth_client):
        """Test creating a new person."""
        response = auth_client.post(
            "/people",
            data={"name": "New Person", "notes": "Test notes"},
            follow_redirects=False,
        )

        assert response.status_code == 302

    def test_create_person_with_image(self, auth_client, sample_image):
        """Test creating a person with reference image."""
        img_file = io.BytesIO(sample_image)

        response = auth_client.post(
            "/people",
            data={"name": "Person With Image", "notes": ""},
            files={"image": ("ref.jpg", img_file, "image/jpeg")},
            follow_redirects=False,
        )

        assert response.status_code == 302

    def test_delete_person(self, auth_client, sample_person):
        """Test deleting a person."""
        response = auth_client.post(
            f"/people/{sample_person.id}/delete",
            follow_redirects=False,
        )

        assert response.status_code == 302

    def test_add_reference_image(self, auth_client, sample_person, sample_image):
        """Test adding reference image to person."""
        img_file = io.BytesIO(sample_image)

        response = auth_client.post(
            f"/people/{sample_person.id}/add-image",
            files={"image": ("ref.jpg", img_file, "image/jpeg")},
            follow_redirects=False,
        )

        assert response.status_code == 302
