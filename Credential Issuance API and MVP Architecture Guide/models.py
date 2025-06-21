from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, JSON, Enum as SQLEnum, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum
import uuid

from .database import Base


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ISSUER_ADMIN = "issuer_admin"
    VERIFIER = "verifier"
    RECIPIENT = "recipient"


class CredentialStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    REVOKED = "revoked"
    EXPIRED = "expired"


class VerificationStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    REVOKED = "revoked"
    EXPIRED = "expired"


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.RECIPIENT)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    profile_picture_url = Column(String(500), nullable=True)
    organization = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    twitter_url = Column(String(500), nullable=True)
    privacy_settings = Column(JSON, nullable=True)  # Store privacy preferences
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    issued_credentials = relationship("Credential", foreign_keys="Credential.issuer_id", back_populates="issuer")
    received_credentials = relationship("Credential", foreign_keys="Credential.recipient_id", back_populates="recipient")
    created_templates = relationship("CredentialTemplate", back_populates="creator")
    oauth_accounts = relationship("OAuthAccount", back_populates="user")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # google, microsoft, linkedin
    provider_user_id = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="oauth_accounts")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    website = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    settings = Column(JSON, nullable=True)  # Organization-specific settings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    templates = relationship("CredentialTemplate", back_populates="organization")
    credentials = relationship("Credential", back_populates="organization")
    members = relationship("OrganizationMember", back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False)  # admin, member, viewer
    permissions = Column(JSON, nullable=True)  # Specific permissions
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User")


class CredentialTemplate(Base):
    __tablename__ = "credential_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    template_type = Column(String(50), nullable=False)  # certificate, badge, diploma
    design_data = Column(JSON, nullable=False)  # Template design configuration
    fields_schema = Column(JSON, nullable=False)  # Dynamic fields schema
    status = Column(SQLEnum(TemplateStatus), default=TemplateStatus.DRAFT)
    is_public = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    tags = Column(JSON, nullable=True)  # Array of tags for categorization
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="templates")
    creator = relationship("User", back_populates="created_templates")
    credentials = relationship("Credential", back_populates="template")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(String(100), unique=True, index=True, nullable=False)  # Public credential ID
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("credential_templates.id"), nullable=False)
    issuer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipient_email = Column(String(255), nullable=False)  # Store email even if user doesn't exist
    recipient_name = Column(String(255), nullable=False)
    
    # Credential data
    credential_data = Column(JSON, nullable=False)  # Dynamic credential fields
    metadata = Column(JSON, nullable=True)  # Additional metadata
    
    # Status and dates
    status = Column(SQLEnum(CredentialStatus), default=CredentialStatus.DRAFT)
    issued_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Files and verification
    pdf_url = Column(String(500), nullable=True)
    png_url = Column(String(500), nullable=True)
    json_ld = Column(JSON, nullable=True)  # JSON-LD representation
    verification_url = Column(String(500), nullable=True)
    qr_code_url = Column(String(500), nullable=True)
    
    # Blockchain integration
    blockchain_hash = Column(String(255), nullable=True)
    blockchain_tx_hash = Column(String(255), nullable=True)
    
    # Privacy and sharing
    is_public = Column(Boolean, default=True)
    sharing_settings = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="credentials")
    template = relationship("CredentialTemplate", back_populates="credentials")
    issuer = relationship("User", foreign_keys=[issuer_id], back_populates="issued_credentials")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_credentials")
    verifications = relationship("CredentialVerification", back_populates="credential")
    analytics_events = relationship("AnalyticsEvent", back_populates="credential")


class CredentialVerification(Base):
    __tablename__ = "credential_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id"), nullable=False)
    verifier_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    verifier_user_agent = Column(Text, nullable=True)
    verification_method = Column(String(50), nullable=False)  # qr_code, url, api
    verification_result = Column(SQLEnum(VerificationStatus), nullable=False)
    verification_details = Column(JSON, nullable=True)  # Additional verification info
    verified_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    credential = relationship("Credential", back_populates="verifications")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # view, download, share, verify
    credential_id = Column(UUID(as_uuid=True), ForeignKey("credentials.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    
    # Event data
    event_data = Column(JSON, nullable=True)  # Additional event-specific data
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    referrer = Column(String(500), nullable=True)
    
    # Geolocation (optional)
    country = Column(String(2), nullable=True)  # ISO country code
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    credential = relationship("Credential", back_populates="analytics_events")
    user = relationship("User")
    organization = relationship("Organization")


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    permissions = Column(JSON, nullable=False)  # API permissions
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organization = relationship("Organization")
    creator = relationship("User")


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    url = Column(String(500), nullable=False)
    events = Column(JSON, nullable=False)  # Array of event types to listen for
    secret = Column(String(255), nullable=False)  # For webhook signature verification
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship("Organization")
    deliveries = relationship("WebhookDelivery", back_populates="endpoint")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint_id = Column(UUID(as_uuid=True), ForeignKey("webhook_endpoints.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(JSON, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    attempts = Column(Integer, default=1)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    endpoint = relationship("WebhookEndpoint", back_populates="deliveries")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)  # credential, template, user, etc.
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")

