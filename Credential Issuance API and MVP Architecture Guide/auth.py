"""
Authentication and authorization utilities.
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt

from .config import settings
from .database import get_db_session
from .models import User, UserRole
from .exceptions import AuthenticationError, AuthorizationError

security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_jwt_token(user_id: str, email: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token for a user."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(user_id: str) -> str:
    """Create a refresh token for a user."""
    expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session)
) -> User:
    """Get the current authenticated user from JWT token."""
    try:
        payload = verify_jwt_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is disabled")
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise AuthenticationError("User account is disabled")
    return current_user


def require_role(required_role: UserRole):
    """Decorator to require a specific user role."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.SUPER_ADMIN:
            raise AuthorizationError(f"Access denied. Required role: {required_role}")
        return current_user
    return role_checker


def require_roles(required_roles: list[UserRole]):
    """Decorator to require one of multiple user roles."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in required_roles and current_user.role != UserRole.SUPER_ADMIN:
            raise AuthorizationError(f"Access denied. Required roles: {required_roles}")
        return current_user
    return role_checker


def check_organization_access(user: User, organization_id: str, db: Session) -> bool:
    """Check if user has access to an organization."""
    from .models import OrganizationMember
    
    # Super admins have access to everything
    if user.role == UserRole.SUPER_ADMIN:
        return True
    
    # Check if user is a member of the organization
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == organization_id
    ).first()
    
    return membership is not None


def check_credential_access(user: User, credential_id: str, db: Session, action: str = "read") -> bool:
    """Check if user has access to a credential."""
    from .models import Credential, OrganizationMember
    
    credential = db.query(Credential).filter(Credential.id == credential_id).first()
    if not credential:
        return False
    
    # Super admins have access to everything
    if user.role == UserRole.SUPER_ADMIN:
        return True
    
    # Recipients can always access their own credentials
    if credential.recipient_id == user.id:
        return True
    
    # Issuers can access credentials they issued
    if credential.issuer_id == user.id:
        return True
    
    # Check organization membership for other actions
    if action in ["write", "delete"]:
        return check_organization_access(user, str(credential.organization_id), db)
    
    # For read access, check if credential is public or user has organization access
    if credential.is_public:
        return True
    
    return check_organization_access(user, str(credential.organization_id), db)


class PermissionChecker:
    """Helper class for checking permissions."""
    
    def __init__(self, user: User, db: Session):
        self.user = user
        self.db = db
    
    def can_issue_credentials(self, organization_id: str) -> bool:
        """Check if user can issue credentials for an organization."""
        if self.user.role in [UserRole.SUPER_ADMIN, UserRole.ISSUER_ADMIN]:
            return check_organization_access(self.user, organization_id, self.db)
        return False
    
    def can_manage_templates(self, organization_id: str) -> bool:
        """Check if user can manage templates for an organization."""
        if self.user.role in [UserRole.SUPER_ADMIN, UserRole.ISSUER_ADMIN]:
            return check_organization_access(self.user, organization_id, self.db)
        return False
    
    def can_view_analytics(self, organization_id: str) -> bool:
        """Check if user can view analytics for an organization."""
        if self.user.role in [UserRole.SUPER_ADMIN, UserRole.ISSUER_ADMIN]:
            return check_organization_access(self.user, organization_id, self.db)
        return False
    
    def can_manage_organization(self, organization_id: str) -> bool:
        """Check if user can manage an organization."""
        if self.user.role == UserRole.SUPER_ADMIN:
            return True
        
        from .models import OrganizationMember
        membership = self.db.query(OrganizationMember).filter(
            OrganizationMember.user_id == self.user.id,
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == "admin"
        ).first()
        
        return membership is not None

