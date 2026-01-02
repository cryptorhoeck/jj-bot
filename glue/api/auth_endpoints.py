"""
Authentication API Endpoints for JJ-Bot
JWT token-based authentication with API key support
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pydantic import BaseModel

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from modules.auth import auth_manager, UserCredentials, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# Request/Response models
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class EnableAuthRequest(BaseModel):
    enabled: bool


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# Dependency for getting current user
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[User]:
    """
    Get current authenticated user from JWT token or API key
    Returns None if auth is disabled
    """
    # If auth is disabled, allow all requests
    if not auth_manager.is_auth_enabled():
        return None

    # Try JWT token first
    if credentials:
        token = credentials.credentials
        payload = auth_manager.verify_token(token)
        if payload:
            # Find user by ID
            user_id = payload.get("sub")
            for user_data in auth_manager.config.users.values():
                if user_data.get('user_id') == user_id:
                    return User(**user_data)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Try API key
    if api_key:
        user = auth_manager.get_user_by_api_key(api_key)
        if user:
            return user
        raise HTTPException(status_code=401, detail="Invalid API key")

    # No credentials provided
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide Bearer token or X-API-Key header."
    )


async def require_admin(
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require admin role for protected endpoints"""
    if not auth_manager.is_auth_enabled():
        return None

    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Public endpoints (no auth required)
@router.get("/status")
async def auth_status():
    """Get authentication status and configuration"""
    status = auth_manager.get_status()
    return {
        "status": "ok",
        **status,
        "message": "Enable auth via POST /api/auth/enable" if not status["auth_enabled"] else "Authentication is active"
    }


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticate user and get JWT tokens

    Returns access_token (short-lived) and refresh_token (long-lived)
    """
    user = auth_manager.authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = auth_manager.create_access_token(user)
    refresh_token = auth_manager.create_refresh_token(user)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=auth_manager.config.access_token_expire_minutes * 60,
        user={
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "last_login": user.last_login
        }
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """Get new access token using refresh token"""
    new_token = auth_manager.refresh_access_token(request.refresh_token)
    if not new_token:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return {
        "access_token": new_token,
        "token_type": "bearer",
        "expires_in": auth_manager.config.access_token_expire_minutes * 60
    }


@router.post("/logout")
async def logout(user: Optional[User] = Depends(get_current_user)):
    """
    Logout user (client should discard tokens)
    Note: JWT tokens are stateless, so logout is client-side
    """
    return {
        "status": "ok",
        "message": "Logged out successfully. Please discard your tokens."
    }


# Protected endpoints (require auth)
@router.get("/me")
async def get_current_user_info(user: Optional[User] = Depends(get_current_user)):
    """Get current user information"""
    if not user:
        return {"status": "ok", "message": "Authentication disabled", "user": None}

    return {
        "status": "ok",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "has_api_key": bool(user.api_key)
        }
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: Optional[User] = Depends(get_current_user)
):
    """Change current user's password"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify current password
    if not auth_manager.verify_password(request.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Update password
    new_hash = auth_manager.hash_password(request.new_password)
    auth_manager.config.users[user.username]['password_hash'] = new_hash
    auth_manager._save_config()

    return {"status": "ok", "message": "Password changed successfully"}


@router.post("/regenerate-api-key")
async def regenerate_api_key(user: Optional[User] = Depends(get_current_user)):
    """Regenerate API key for current user"""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    new_key = auth_manager.regenerate_api_key(user.username)
    if not new_key:
        raise HTTPException(status_code=500, detail="Failed to regenerate API key")

    return {
        "status": "ok",
        "api_key": new_key,
        "message": "API key regenerated. Old key is now invalid."
    }


# Admin endpoints
@router.post("/enable")
async def enable_auth(
    request: EnableAuthRequest,
    admin: Optional[User] = Depends(require_admin)
):
    """Enable or disable authentication (admin only, or when no users exist)"""
    # Allow enabling auth if no users exist (first-time setup)
    if not auth_manager.config.users:
        # Setup default admin
        creds = auth_manager.setup_default_admin()
        auth_manager.enable_auth(request.enabled)

        return {
            "status": "ok",
            "auth_enabled": request.enabled,
            "message": "Authentication enabled with default admin user",
            "admin_credentials": creds if request.enabled else None,
            "warning": "SAVE THESE CREDENTIALS - They will only be shown once!" if creds else None
        }

    auth_manager.enable_auth(request.enabled)
    return {
        "status": "ok",
        "auth_enabled": request.enabled,
        "message": f"Authentication {'enabled' if request.enabled else 'disabled'}"
    }


@router.post("/users", dependencies=[Depends(require_admin)])
async def create_user(request: CreateUserRequest):
    """Create a new user (admin only)"""
    if request.role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'")

    user = auth_manager.create_user(request.username, request.password, request.role)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")

    return {
        "status": "ok",
        "message": f"User '{request.username}' created successfully",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "api_key": user.api_key
        }
    }


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users():
    """List all users (admin only)"""
    users = []
    for username, user_data in auth_manager.config.users.items():
        users.append({
            "user_id": user_data.get('user_id'),
            "username": username,
            "role": user_data.get('role'),
            "created_at": user_data.get('created_at'),
            "last_login": user_data.get('last_login'),
            "has_api_key": bool(user_data.get('api_key'))
        })

    return {
        "status": "ok",
        "users": users,
        "total": len(users)
    }


@router.delete("/users/{username}", dependencies=[Depends(require_admin)])
async def delete_user(username: str):
    """Delete a user (admin only)"""
    if username not in auth_manager.config.users:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent deleting last admin
    admins = [u for u in auth_manager.config.users.values() if u.get('role') == 'admin']
    if len(admins) == 1 and auth_manager.config.users[username].get('role') == 'admin':
        raise HTTPException(status_code=400, detail="Cannot delete the last admin user")

    del auth_manager.config.users[username]
    auth_manager._save_config()

    return {
        "status": "ok",
        "message": f"User '{username}' deleted successfully"
    }


@router.post("/setup")
async def setup_first_user(request: CreateUserRequest):
    """
    First-time setup - create initial admin user
    Only works when no users exist
    """
    if auth_manager.config.users:
        raise HTTPException(
            status_code=400,
            detail="Setup already completed. Use /api/auth/login to authenticate."
        )

    # Create admin user
    user = auth_manager.create_user(request.username, request.password, role="admin")
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")

    # Enable auth by default for security
    auth_manager.enable_auth(True)

    return {
        "status": "ok",
        "message": "Initial setup complete. Authentication is now enabled.",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role,
            "api_key": user.api_key
        },
        "auth_enabled": True
    }
