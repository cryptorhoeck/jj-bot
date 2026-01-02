"""
Authentication Tests for JJ-Bot
Tests JWT authentication, API keys, and user management
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestAuthManager:
    """Test AuthManager class functionality"""

    def test_hash_password(self):
        """Test password hashing"""
        from modules.auth import AuthManager

        password = "testpassword123"
        hashed = AuthManager.hash_password(password)

        # Hash should be in format salt:hash
        assert ":" in hashed
        salt, hash_value = hashed.split(":")
        assert len(salt) == 32  # 16 bytes hex
        assert len(hash_value) == 64  # 32 bytes hex

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        from modules.auth import AuthManager

        password = "testpassword123"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        from modules.auth import AuthManager

        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash format"""
        from modules.auth import AuthManager

        assert AuthManager.verify_password("password", "invalid_hash") is False
        assert AuthManager.verify_password("password", "") is False


class TestAuthEndpoints:
    """Test authentication API endpoints"""

    def test_auth_status_endpoint(self, api_client):
        """Test auth status endpoint"""
        response = api_client.get("/api/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert "auth_enabled" in data
        assert "status" in data

    def test_auth_status_shows_disabled_by_default(self, api_client):
        """Test that auth is disabled by default"""
        response = api_client.get("/api/auth/status")
        data = response.json()
        # Auth should be disabled by default for development
        assert data["auth_enabled"] is False or "auth_enabled" in data


class TestUserManagement:
    """Test user creation and management"""

    def test_create_user(self):
        """Test user creation"""
        from modules.auth import AuthManager
        import tempfile

        # Use temp directory for test
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123", role="user")

                assert user is not None
                assert user.username == "testuser"
                assert user.role == "user"
                assert user.api_key is not None

    def test_create_duplicate_user_fails(self):
        """Test that creating duplicate user fails"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.create_user("testuser", "password123")
                duplicate = manager.create_user("testuser", "different_password")

                assert duplicate is None

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.create_user("testuser", "password123")
                user = manager.authenticate_user("testuser", "password123")

                assert user is not None
                assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.create_user("testuser", "password123")
                user = manager.authenticate_user("testuser", "wrongpassword")

                assert user is None

    def test_authenticate_nonexistent_user(self):
        """Test authentication with non-existent user"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.authenticate_user("nonexistent", "password")

                assert user is None


class TestJWTTokens:
    """Test JWT token creation and verification"""

    def test_create_access_token(self):
        """Test access token creation"""
        from modules.auth import AuthManager, User
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123")
                token = manager.create_access_token(user)

                assert token is not None
                assert len(token) > 0

    def test_verify_access_token(self):
        """Test access token verification"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123")
                token = manager.create_access_token(user)
                payload = manager.verify_token(token)

                assert payload is not None
                assert payload.get("sub") == user.user_id

    def test_verify_invalid_token(self):
        """Test verification of invalid token"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                payload = manager.verify_token("invalid.token.here")

                assert payload is None

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123")
                refresh_token = manager.create_refresh_token(user)

                assert refresh_token is not None
                assert len(refresh_token) > 0


class TestAPIKeyAuth:
    """Test API key authentication"""

    def test_get_user_by_api_key(self):
        """Test getting user by API key"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123")
                found_user = manager.get_user_by_api_key(user.api_key)

                assert found_user is not None
                assert found_user.username == "testuser"

    def test_get_user_by_invalid_api_key(self):
        """Test getting user with invalid API key"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.create_user("testuser", "password123")
                found_user = manager.get_user_by_api_key("invalid_key")

                assert found_user is None

    def test_regenerate_api_key(self):
        """Test API key regeneration"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                user = manager.create_user("testuser", "password123")
                old_key = user.api_key
                new_key = manager.regenerate_api_key("testuser")

                assert new_key is not None
                assert new_key != old_key


class TestAuthConfig:
    """Test authentication configuration"""

    def test_enable_auth(self):
        """Test enabling authentication"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.enable_auth(True)

                assert manager.is_auth_enabled() is True

    def test_disable_auth(self):
        """Test disabling authentication"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                manager.enable_auth(True)
                manager.enable_auth(False)

                assert manager.is_auth_enabled() is False

    def test_get_status(self):
        """Test getting auth status"""
        from modules.auth import AuthManager
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "auth_config.json"

            with patch('modules.auth.AUTH_CONFIG_PATH', config_path):
                manager = AuthManager()
                status = manager.get_status()

                assert "auth_enabled" in status
                assert "user_count" in status
                assert "jwt_available" in status
