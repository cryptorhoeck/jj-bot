import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from pathlib import Path
import json
import secrets
import hashlib

class EnterpriseAuthManager:
    """Enterprise authentication and authorization system"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = self.get_or_create_secret_key()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60
        self.users_db = self.load_users_db()
        self.api_keys_db = self.load_api_keys_db()
        
    def get_or_create_secret_key(self) -> str:
        """Get or create JWT secret key"""
        secret_file = Path.home() / "jj-bot" / "ops" / "security" / ".secret_key"
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        
        if secret_file.exists():
            return secret_file.read_text().strip()
        else:
            # Generate new secret key
            secret_key = secrets.token_urlsafe(64)
            secret_file.write_text(secret_key)
            secret_file.chmod(0o600)  # Read-only for owner
            return secret_key
    
    def load_users_db(self) -> Dict:
        """Load users database"""
        users_file = Path.home() / "jj-bot" / "ops" / "security" / "users.json"
        
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.create_default_users()
        else:
            return self.create_default_users()
    
    def create_default_users(self) -> Dict:
        """Create default admin user"""
        default_users = {
            "admin": {
                "username": "admin",
                "email": "admin@jj-bot.local",
                "hashed_password": self.get_password_hash("jj-gorilla-2024"),
                "role": "admin",
                "permissions": ["read", "write", "admin", "backup", "restore"],
                "created_at": datetime.now().isoformat(),
                "last_login": None,
                "active": True
            }
        }
        
        self.save_users_db(default_users)
        return default_users
    
    def save_users_db(self, users_db: Dict = None):
        """Save users database"""
        if users_db:
            self.users_db = users_db
            
        users_file = Path.home() / "jj-bot" / "ops" / "security" / "users.json"
        users_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(users_file, 'w') as f:
            json.dump(self.users_db, f, indent=2)
        
        users_file.chmod(0o600)  # Secure permissions
    
    def load_api_keys_db(self) -> Dict:
        """Load API keys database"""
        api_keys_file = Path.home() / "jj-bot" / "ops" / "security" / "api_keys.json"
        
        if api_keys_file.exists():
            try:
                with open(api_keys_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        else:
            return {}
    
    def save_api_keys_db(self, api_keys_db: Dict = None):
        """Save API keys database"""
        if api_keys_db:
            self.api_keys_db = api_keys_db
            
        api_keys_file = Path.home() / "jj-bot" / "ops" / "security" / "api_keys.json"
        api_keys_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(api_keys_file, 'w') as f:
            json.dump(self.api_keys_db, f, indent=2)
        
        api_keys_file.chmod(0o600)  # Secure permissions
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash password"""
        return self.pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        user = self.users_db.get(username)
        if not user:
            return None
        
        if not user.get("active", True):
            return None
            
        if not self.verify_password(password, user["hashed_password"]):
            return None
        
        # Update last login
        user["last_login"] = datetime.now().isoformat()
        self.save_users_db()
        
        return user
    
    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            
            if username is None:
                return None
                
            # Check if user still exists and is active
            user = self.users_db.get(username)
            if not user or not user.get("active", True):
                return None
                
            return payload
            
        except jwt.PyJWTError:
            return None
    
    def create_api_key(self, name: str, permissions: list, expires_in_days: int = 365) -> Dict:
        """Create API key"""
        api_key = secrets.token_urlsafe(32)
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        key_data = {
            "key_id": key_id,
            "name": name,
            "hashed_key": self.get_password_hash(api_key),
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "last_used": None,
            "usage_count": 0,
            "active": True
        }
        
        self.api_keys_db[key_id] = key_data
        self.save_api_keys_db()
        
        return {
            "api_key": api_key,
            "key_id": key_id,
            "expires_at": expires_at.isoformat()
        }
    
    def verify_api_key(self, api_key: str) -> Optional[Dict]:
        """Verify API key"""
        key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        key_data = self.api_keys_db.get(key_id)
        
        if not key_data:
            return None
        
        if not key_data.get("active", True):
            return None
        
        # Check expiration
        expires_at = datetime.fromisoformat(key_data["expires_at"])
        if datetime.now() > expires_at:
            return None
        
        # Verify key
        if not self.verify_password(api_key, key_data["hashed_key"]):
            return None
        
        # Update usage
        key_data["last_used"] = datetime.now().isoformat()
        key_data["usage_count"] = key_data.get("usage_count", 0) + 1
        self.save_api_keys_db()
        
        return key_data
    
    def has_permission(self, user_or_key: Dict, required_permission: str) -> bool:
        """Check if user or API key has required permission"""
        permissions = user_or_key.get("permissions", [])
        
        # Admin has all permissions
        if "admin" in permissions:
            return True
        
        return required_permission in permissions
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Dict:
        """Create new user"""
        if username in self.users_db:
            raise ValueError(f"User {username} already exists")
        
        permissions = {
            "admin": ["read", "write", "admin", "backup", "restore"],
            "trader": ["read", "write"],
            "viewer": ["read"]
        }.get(role, ["read"])
        
        user_data = {
            "username": username,
            "email": email,
            "hashed_password": self.get_password_hash(password),
            "role": role,
            "permissions": permissions,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "active": True
        }
        
        self.users_db[username] = user_data
        self.save_users_db()
        
        return user_data
    
    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        active_users = len([u for u in self.users_db.values() if u.get("active", True)])
        active_api_keys = len([k for k in self.api_keys_db.values() if k.get("active", True)])
        
        # Recent logins (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_logins = 0
        
        for user in self.users_db.values():
            if user.get("last_login"):
                try:
                    last_login = datetime.fromisoformat(user["last_login"])
                    if last_login > recent_cutoff:
                        recent_logins += 1
                except:
                    pass
        
        return {
            "total_users": len(self.users_db),
            "active_users": active_users,
            "total_api_keys": len(self.api_keys_db),
            "active_api_keys": active_api_keys,
            "recent_logins_24h": recent_logins,
            "auth_system": "enabled"
        }

# Global auth manager instance
auth_manager = EnterpriseAuthManager()
