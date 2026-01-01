"""
JWT Authentication Module for JJ-Bot
Provides secure authentication with JWT tokens and API keys
"""

import os
import json
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# JWT handling
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configuration paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
AUTH_CONFIG_PATH = CONFIG_DIR / "auth_config.json"


class TokenData(BaseModel):
    """Token payload data"""
    username: str
    user_id: str
    role: str = "user"
    exp: Optional[datetime] = None


class UserCredentials(BaseModel):
    """User login credentials"""
    username: str
    password: str


class User(BaseModel):
    """User model"""
    user_id: str
    username: str
    password_hash: str
    role: str = "user"  # user, admin
    created_at: str
    last_login: Optional[str] = None
    api_key: Optional[str] = None


class AuthConfig(BaseModel):
    """Authentication configuration"""
    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    api_key_enabled: bool = True
    users: Dict[str, Dict[str, Any]] = {}


class AuthManager:
    """Manages authentication and user sessions"""

    def __init__(self):
        self.config = self._load_config()
        self._ensure_jwt_secret()

    def _load_config(self) -> AuthConfig:
        """Load auth configuration from file"""
        try:
            if AUTH_CONFIG_PATH.exists():
                with open(AUTH_CONFIG_PATH) as f:
                    data = json.load(f)
                    return AuthConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load auth config: {e}")
        return AuthConfig()

    def _save_config(self):
        """Save auth configuration to file"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(AUTH_CONFIG_PATH, 'w') as f:
                json.dump(self.config.model_dump(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save auth config: {e}")

    def _ensure_jwt_secret(self):
        """Ensure JWT secret exists"""
        if not self.config.jwt_secret:
            self.config.jwt_secret = secrets.token_urlsafe(64)
            self._save_config()
            logger.info("Generated new JWT secret")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        ).hex()
        return f"{salt}:{pwd_hash}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = password_hash.split(':')
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            ).hex()
            return secrets.compare_digest(pwd_hash, new_hash)
        except Exception:
            return False

    def create_user(self, username: str, password: str, role: str = "user") -> Optional[User]:
        """Create a new user"""
        if username in self.config.users:
            logger.warning(f"User already exists: {username}")
            return None

        user = User(
            user_id=secrets.token_urlsafe(16),
            username=username,
            password_hash=self.hash_password(password),
            role=role,
            created_at=datetime.now().isoformat(),
            api_key=secrets.token_urlsafe(32)
        )

        self.config.users[username] = user.model_dump()
        self._save_config()
        logger.info(f"Created user: {username} with role: {role}")
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        if username not in self.config.users:
            return None

        user_data = self.config.users[username]
        if not self.verify_password(password, user_data['password_hash']):
            return None

        # Update last login
        user_data['last_login'] = datetime.now().isoformat()
        self.config.users[username] = user_data
        self._save_config()

        return User(**user_data)

    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key"""
        for user_data in self.config.users.values():
            if user_data.get('api_key') == api_key:
                return User(**user_data)
        return None

    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        if not JWT_AVAILABLE:
            # Fallback to simple token
            return f"simple:{user.user_id}:{secrets.token_urlsafe(16)}"

        expire = datetime.utcnow() + timedelta(minutes=self.config.access_token_expire_minutes)
        payload = {
            "sub": user.user_id,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "type": "access"
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)

    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        if not JWT_AVAILABLE:
            return f"refresh:{user.user_id}:{secrets.token_urlsafe(32)}"

        expire = datetime.utcnow() + timedelta(days=self.config.refresh_token_expire_days)
        payload = {
            "sub": user.user_id,
            "type": "refresh",
            "exp": expire
        }
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        if not JWT_AVAILABLE:
            # Simple token validation
            if token.startswith("simple:") or token.startswith("refresh:"):
                parts = token.split(":")
                if len(parts) >= 2:
                    return {"sub": parts[1], "username": "user"}
            return None

        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Generate new access token from refresh token"""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        for user_data in self.config.users.values():
            if user_data.get('user_id') == user_id:
                user = User(**user_data)
                return self.create_access_token(user)
        return None

    def regenerate_api_key(self, username: str) -> Optional[str]:
        """Regenerate API key for user"""
        if username not in self.config.users:
            return None

        new_key = secrets.token_urlsafe(32)
        self.config.users[username]['api_key'] = new_key
        self._save_config()
        return new_key

    def enable_auth(self, enabled: bool = True):
        """Enable or disable authentication"""
        self.config.auth_enabled = enabled
        self._save_config()
        logger.info(f"Authentication {'enabled' if enabled else 'disabled'}")

    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled"""
        return self.config.auth_enabled

    def get_status(self) -> Dict[str, Any]:
        """Get authentication status"""
        return {
            "auth_enabled": self.config.auth_enabled,
            "jwt_available": JWT_AVAILABLE,
            "api_key_enabled": self.config.api_key_enabled,
            "user_count": len(self.config.users),
            "access_token_expire_minutes": self.config.access_token_expire_minutes,
            "refresh_token_expire_days": self.config.refresh_token_expire_days
        }

    def setup_default_admin(self) -> Optional[Dict[str, str]]:
        """Create default admin user if no users exist"""
        if self.config.users:
            return None

        # Generate secure random password
        password = secrets.token_urlsafe(12)
        user = self.create_user("admin", password, role="admin")

        if user:
            logger.info("Created default admin user")
            return {
                "username": "admin",
                "password": password,
                "api_key": user.api_key
            }
        return None


# Global auth manager instance
auth_manager = AuthManager()
