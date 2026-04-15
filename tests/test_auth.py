import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from tests.conftest import *


class TestRegistration:
    """Tests for user registration flow."""

    def test_register_page_loads(self, test_client: TestClient):
        """GET /auth/register returns the registration page."""
        response = test_client.get("/auth/register", follow_redirects=False)
        assert response.status_code == 200
        assert b"Create your account" in response.content

    def test_register_with_valid_data_redirects_to_login(self, test_client: TestClient):
        """POST /auth/register with valid data creates user and redirects to login."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    def test_register_with_duplicate_username_returns_error(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/register with existing username returns 400 with error message."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "Another User",
                "email": "another@example.com",
                "username": "testuser",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Username already exists" in response.content

    def test_register_with_duplicate_email_returns_error(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/register with existing email returns 400 with error message."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "Another User",
                "email": "testuser@example.com",
                "username": "differentuser",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Email already exists" in response.content

    def test_register_with_mismatched_passwords_returns_error(
        self, test_client: TestClient
    ):
        """POST /auth/register with mismatched passwords returns 400 with error."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "confirm_password": "differentpassword",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Passwords do not match" in response.content

    def test_register_with_short_password_returns_error(self, test_client: TestClient):
        """POST /auth/register with password shorter than 8 chars returns 400."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "short",
                "confirm_password": "short",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Password must be at least 8 characters" in response.content

    def test_register_with_missing_username_returns_error(self, test_client: TestClient):
        """POST /auth/register with empty username returns 400."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "newuser@example.com",
                "username": "",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Username is required" in response.content

    def test_register_with_missing_display_name_returns_error(
        self, test_client: TestClient
    ):
        """POST /auth/register with empty display name returns 400."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "",
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Display name is required" in response.content

    def test_register_with_missing_email_returns_error(self, test_client: TestClient):
        """POST /auth/register with empty email returns 400."""
        response = test_client.post(
            "/auth/register",
            data={
                "display_name": "New User",
                "email": "",
                "username": "newuser",
                "password": "securepassword123",
                "confirm_password": "securepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Email is required" in response.content

    def test_register_redirects_authenticated_user_to_dashboard(
        self, authenticated_client: TestClient
    ):
        """GET /auth/register redirects already-authenticated user to dashboard."""
        response = authenticated_client.get("/auth/register", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    def test_register_redirects_admin_to_admin_dashboard(
        self, admin_client: TestClient
    ):
        """GET /auth/register redirects admin user to admin dashboard."""
        response = admin_client.get("/auth/register", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard"


class TestLogin:
    """Tests for user login flow."""

    def test_login_page_loads(self, test_client: TestClient):
        """GET /auth/login returns the login page."""
        response = test_client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 200
        assert b"Sign in to FitLog" in response.content

    def test_login_with_valid_credentials_redirects_to_dashboard(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/login with valid credentials sets cookie and redirects to dashboard."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "testpassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"
        assert "access_token" in response.cookies

    def test_login_admin_redirects_to_admin_dashboard(
        self, test_client: TestClient, admin_user
    ):
        """POST /auth/login with admin credentials redirects to admin dashboard."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "adminuser",
                "password": "adminpassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard"
        assert "access_token" in response.cookies

    def test_login_with_invalid_password_returns_error(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/login with wrong password returns 401 with error message."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "wrongpassword",
            },
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert b"Invalid username or password" in response.content

    def test_login_with_nonexistent_username_returns_error(
        self, test_client: TestClient
    ):
        """POST /auth/login with non-existent username returns 401."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "nonexistentuser",
                "password": "somepassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 401
        assert b"Invalid username or password" in response.content

    def test_login_with_empty_fields_returns_error(self, test_client: TestClient):
        """POST /auth/login with empty username and password returns 400."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "",
                "password": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Username and password are required" in response.content

    def test_login_with_empty_password_returns_error(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/login with empty password returns 400."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "testuser",
                "password": "",
            },
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert b"Username and password are required" in response.content

    def test_login_redirects_authenticated_user_to_dashboard(
        self, authenticated_client: TestClient
    ):
        """GET /auth/login redirects already-authenticated user to dashboard."""
        response = authenticated_client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    def test_login_redirects_admin_to_admin_dashboard(
        self, admin_client: TestClient
    ):
        """GET /auth/login redirects admin user to admin dashboard."""
        response = admin_client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard"

    def test_login_is_case_insensitive_for_username(
        self, test_client: TestClient, test_user
    ):
        """POST /auth/login accepts username in different case."""
        response = test_client.post(
            "/auth/login",
            data={
                "username": "TestUser",
                "password": "testpassword123",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"


class TestLogout:
    """Tests for user logout flow."""

    def test_logout_get_clears_cookie_and_redirects(
        self, authenticated_client: TestClient
    ):
        """GET /auth/logout clears the access_token cookie and redirects to login."""
        response = authenticated_client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header

    def test_logout_post_clears_cookie_and_redirects(
        self, authenticated_client: TestClient
    ):
        """POST /auth/logout clears the access_token cookie and redirects to login."""
        response = authenticated_client.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token" in set_cookie_header


class TestProtectedRoutes:
    """Tests that protected routes redirect unauthenticated users."""

    def test_dashboard_redirects_unauthenticated_user(self, test_client: TestClient):
        """GET /dashboard returns 401 for unauthenticated user."""
        response = test_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 401

    def test_exercises_redirects_unauthenticated_user(self, test_client: TestClient):
        """GET /exercises returns 401 for unauthenticated user."""
        response = test_client.get("/exercises", follow_redirects=False)
        assert response.status_code == 401

    def test_workouts_history_redirects_unauthenticated_user(
        self, test_client: TestClient
    ):
        """GET /workouts/history returns 401 for unauthenticated user."""
        response = test_client.get("/workouts/history", follow_redirects=False)
        assert response.status_code == 401

    def test_measurements_redirects_unauthenticated_user(
        self, test_client: TestClient
    ):
        """GET /measurements returns 401 for unauthenticated user."""
        response = test_client.get("/measurements", follow_redirects=False)
        assert response.status_code == 401

    def test_progress_redirects_unauthenticated_user(self, test_client: TestClient):
        """GET /progress returns 401 for unauthenticated user."""
        response = test_client.get("/progress", follow_redirects=False)
        assert response.status_code == 401

    def test_profile_redirects_unauthenticated_user(self, test_client: TestClient):
        """GET /profile returns 401 for unauthenticated user."""
        response = test_client.get("/profile", follow_redirects=False)
        assert response.status_code == 401

    def test_templates_redirects_unauthenticated_user(self, test_client: TestClient):
        """GET /templates returns 401 for unauthenticated user."""
        response = test_client.get("/templates", follow_redirects=False)
        assert response.status_code == 401

    def test_admin_dashboard_redirects_unauthenticated_user(
        self, test_client: TestClient
    ):
        """GET /admin/dashboard returns 401 for unauthenticated user."""
        response = test_client.get("/admin/dashboard", follow_redirects=False)
        assert response.status_code == 401

    def test_admin_dashboard_forbidden_for_regular_user(
        self, authenticated_client: TestClient
    ):
        """GET /admin/dashboard returns 403 for non-admin user."""
        response = authenticated_client.get(
            "/admin/dashboard", follow_redirects=False
        )
        assert response.status_code == 403

    def test_admin_dashboard_accessible_for_admin(self, admin_client: TestClient):
        """GET /admin/dashboard returns 200 for admin user."""
        response = admin_client.get("/admin/dashboard", follow_redirects=False)
        assert response.status_code == 200

    def test_authenticated_user_can_access_dashboard(
        self, authenticated_client: TestClient
    ):
        """GET /dashboard returns 200 for authenticated user."""
        response = authenticated_client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 200

    def test_authenticated_user_can_access_exercises(
        self, authenticated_client: TestClient
    ):
        """GET /exercises returns 200 for authenticated user."""
        response = authenticated_client.get("/exercises", follow_redirects=False)
        assert response.status_code == 200

    def test_authenticated_user_can_access_profile(
        self, authenticated_client: TestClient
    ):
        """GET /profile returns 200 for authenticated user."""
        response = authenticated_client.get("/profile", follow_redirects=False)
        assert response.status_code == 200


class TestRootRedirect:
    """Tests for the root URL redirect behavior."""

    def test_root_redirects_unauthenticated_to_login(self, test_client: TestClient):
        """GET / redirects unauthenticated user to login page."""
        response = test_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/auth/login"

    def test_root_redirects_authenticated_user_to_dashboard(
        self, authenticated_client: TestClient
    ):
        """GET / redirects authenticated regular user to dashboard."""
        response = authenticated_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

    def test_root_redirects_admin_to_admin_dashboard(
        self, admin_client: TestClient
    ):
        """GET / redirects admin user to admin dashboard."""
        response = admin_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/admin/dashboard"


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, test_client: TestClient):
        """GET /health returns 200 with status ok."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}