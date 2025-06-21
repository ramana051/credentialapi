"""
Credential Issuance Service

This service handles the creation, management, and issuance of digital credentials.
It provides both API endpoints and business logic for credential operations.
"""
from fastapi import FastAPI

app = FastAPI()

# Define routes here

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

# Import shared modules
import sys
sys.path.append('/home/ubuntu/digital-credentials-platform/backend')

from shared.database import get_db_session, create_tables
from shared.models import Credential, CredentialTemplate, User, Organization, CredentialStatus, UserRole
from shared.auth import get_current_user, require_roles, PermissionChecker
from shared.exceptions import ValidationError, NotFoundError, AuthorizationError, CredentialError
from shared.utils import (
    generate_credential_id, generate_qr_code, generate_verification_url,
    create_json_ld_credential, calculate_file_hash, sanitize_filename
)
from shared.config import settings

# Pydantic models for request/response
from pydantic import BaseModel, EmailStr, validator
from enum import Enum


class CredentialCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    template_id: str
    recipient_email: EmailStr
    recipient_name: str
    credential_data: Dict[str, Any] = {}
    expires_at: Optional[datetime] = None
    is_public: bool = True
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return v.strip()


class BulkCredentialCreateRequest(BaseModel):
    template_id: str
    credentials: List[Dict[str, Any]]
    default_expires_at: Optional[datetime] = None
    default_is_public: bool = True


class CredentialUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    credential_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    is_public: Optional[bool] = None


class CredentialResponse(BaseModel):
    id: str
    credential_id: str
    title: str
    description: Optional[str]
    status: str
    recipient_email: str
    recipient_name: str
    issued_at: Optional[datetime]
    expires_at: Optional[datetime]
    verification_url: Optional[str]
    pdf_url: Optional[str]
    png_url: Optional[str]
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Initialize FastAPI app
app = FastAPI(
    title="Digital Credentials Platform - Credential Issuance Service",
    description="Service for issuing and managing digital credentials",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
upload_dir = Path(settings.upload_directory)
upload_dir.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    create_tables()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "credential-issuance"}


@app.post("/credentials", response_model=CredentialResponse)
async def create_credential(
    request: CredentialCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create a new credential."""
    
    # Check permissions
    permission_checker = PermissionChecker(current_user, db)
    
    # Get template to verify organization access
    template = db.query(CredentialTemplate).filter(
        CredentialTemplate.id == request.template_id
    ).first()
    
    if not template:
        raise NotFoundError("Template not found")
    
    if not permission_checker.can_issue_credentials(str(template.organization_id)):
        raise AuthorizationError("You don't have permission to issue credentials for this organization")
    
    # Check if recipient exists, create if not
    recipient = db.query(User).filter(User.email == request.recipient_email).first()
    if not recipient:
        # Create a basic recipient user
        recipient = User(
            email=request.recipient_email,
            first_name=request.recipient_name.split()[0] if request.recipient_name else "Unknown",
            last_name=" ".join(request.recipient_name.split()[1:]) if len(request.recipient_name.split()) > 1 else "",
            role=UserRole.RECIPIENT,
            is_active=True
        )
        db.add(recipient)
        db.flush()  # Get the ID
    
    # Generate credential
    credential_id = generate_credential_id()
    verification_url = generate_verification_url(credential_id)
    
    # Create credential record
    credential = Credential(
        credential_id=credential_id,
        title=request.title,
        description=request.description,
        organization_id=template.organization_id,
        template_id=template.id,
        issuer_id=current_user.id,
        recipient_id=recipient.id,
        recipient_email=request.recipient_email,
        recipient_name=request.recipient_name,
        credential_data=request.credential_data,
        status=CredentialStatus.DRAFT,
        expires_at=request.expires_at,
        verification_url=verification_url,
        is_public=request.is_public
    )
    
    db.add(credential)
    db.commit()
    db.refresh(credential)
    
    # Generate credential files in background
    background_tasks.add_task(
        generate_credential_files,
        credential.id,
        template.design_data
    )
    
    return CredentialResponse.from_orm(credential)


@app.post("/credentials/bulk", response_model=List[CredentialResponse])
async def create_bulk_credentials(
    request: BulkCredentialCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Create multiple credentials in bulk."""
    
    # Check permissions
    permission_checker = PermissionChecker(current_user, db)
    
    # Get template
    template = db.query(CredentialTemplate).filter(
        CredentialTemplate.id == request.template_id
    ).first()
    
    if not template:
        raise NotFoundError("Template not found")
    
    if not permission_checker.can_issue_credentials(str(template.organization_id)):
        raise AuthorizationError("You don't have permission to issue credentials for this organization")
    
    created_credentials = []
    
    for cred_data in request.credentials:
        # Validate required fields
        if 'recipient_email' not in cred_data or 'recipient_name' not in cred_data:
            continue  # Skip invalid entries
        
        # Check if recipient exists
        recipient = db.query(User).filter(
            User.email == cred_data['recipient_email']
        ).first()
        
        if not recipient:
            # Create recipient user
            name_parts = cred_data['recipient_name'].split()
            recipient = User(
                email=cred_data['recipient_email'],
                first_name=name_parts[0] if name_parts else "Unknown",
                last_name=" ".join(name_parts[1:]) if len(name_parts) > 1 else "",
                role=UserRole.RECIPIENT,
                is_active=True
            )
            db.add(recipient)
            db.flush()
        
        # Generate credential
        credential_id = generate_credential_id()
        verification_url = generate_verification_url(credential_id)
        
        credential = Credential(
            credential_id=credential_id,
            title=cred_data.get('title', template.name),
            description=cred_data.get('description', template.description),
            organization_id=template.organization_id,
            template_id=template.id,
            issuer_id=current_user.id,
            recipient_id=recipient.id,
            recipient_email=cred_data['recipient_email'],
            recipient_name=cred_data['recipient_name'],
            credential_data=cred_data.get('credential_data', {}),
            status=CredentialStatus.DRAFT,
            expires_at=cred_data.get('expires_at', request.default_expires_at),
            verification_url=verification_url,
            is_public=cred_data.get('is_public', request.default_is_public)
        )
        
        db.add(credential)
        created_credentials.append(credential)
    
    db.commit()
    
    # Generate files for all credentials in background
    for credential in created_credentials:
        background_tasks.add_task(
            generate_credential_files,
            credential.id,
            template.design_data
        )
    
    return [CredentialResponse.from_orm(cred) for cred in created_credentials]


@app.get("/credentials", response_model=List[CredentialResponse])
async def list_credentials(
    organization_id: Optional[str] = None,
    status: Optional[str] = None,
    recipient_email: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """List credentials with filtering options."""
    
    query = db.query(Credential)
    
    # Apply filters based on user role and permissions
    if current_user.role == UserRole.RECIPIENT:
        # Recipients can only see their own credentials
        query = query.filter(Credential.recipient_id == current_user.id)
    elif current_user.role in [UserRole.ISSUER_ADMIN, UserRole.VERIFIER]:
        # Issuers and verifiers can see organization credentials
        if organization_id:
            permission_checker = PermissionChecker(current_user, db)
            if not permission_checker.can_view_analytics(organization_id):
                raise AuthorizationError("Access denied to organization credentials")
            query = query.filter(Credential.organization_id == organization_id)
        else:
            # Show credentials from organizations they have access to
            from shared.models import OrganizationMember
            org_ids = db.query(OrganizationMember.organization_id).filter(
                OrganizationMember.user_id == current_user.id
            ).subquery()
            query = query.filter(Credential.organization_id.in_(org_ids))
    
    # Apply additional filters
    if status:
        query = query.filter(Credential.status == status)
    
    if recipient_email:
        query = query.filter(Credential.recipient_email.ilike(f"%{recipient_email}%"))
    
    # Apply pagination
    credentials = query.offset(skip).limit(limit).all()
    
    return [CredentialResponse.from_orm(cred) for cred in credentials]


@app.get("/credentials/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Get a specific credential."""
    
    credential = db.query(Credential).filter(
        Credential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise NotFoundError("Credential not found")
    
    # Check access permissions
    from shared.auth import check_credential_access
    if not check_credential_access(current_user, str(credential.id), db):
        raise AuthorizationError("Access denied to this credential")
    
    return CredentialResponse.from_orm(credential)


@app.put("/credentials/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    request: CredentialUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Update a credential."""
    
    credential = db.query(Credential).filter(
        Credential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise NotFoundError("Credential not found")
    
    # Check permissions
    from shared.auth import check_credential_access
    if not check_credential_access(current_user, str(credential.id), db, "write"):
        raise AuthorizationError("Access denied to modify this credential")
    
    # Update fields
    if request.title is not None:
        credential.title = request.title
    if request.description is not None:
        credential.description = request.description
    if request.credential_data is not None:
        credential.credential_data = request.credential_data
    if request.expires_at is not None:
        credential.expires_at = request.expires_at
    if request.is_public is not None:
        credential.is_public = request.is_public
    
    credential.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(credential)
    
    # Regenerate files if data changed
    if request.credential_data is not None or request.title is not None:
        template = db.query(CredentialTemplate).filter(
            CredentialTemplate.id == credential.template_id
        ).first()
        
        if template:
            background_tasks.add_task(
                generate_credential_files,
                credential.id,
                template.design_data
            )
    
    return CredentialResponse.from_orm(credential)


@app.post("/credentials/{credential_id}/issue")
async def issue_credential(
    credential_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Issue a credential (change status from draft to issued)."""
    
    credential = db.query(Credential).filter(
        Credential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise NotFoundError("Credential not found")
    
    # Check permissions
    from shared.auth import check_credential_access
    if not check_credential_access(current_user, str(credential.id), db, "write"):
        raise AuthorizationError("Access denied to issue this credential")
    
    if credential.status != CredentialStatus.DRAFT:
        raise CredentialError("Only draft credentials can be issued")
    
    # Update status
    credential.status = CredentialStatus.ISSUED
    credential.issued_at = datetime.utcnow()
    
    db.commit()
    
    # Send notification to recipient
    background_tasks.add_task(
        send_credential_notification,
        credential.id
    )
    
    return {"message": "Credential issued successfully", "credential_id": credential_id}


@app.post("/credentials/{credential_id}/revoke")
async def revoke_credential(
    credential_id: str,
    reason: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Revoke a credential."""
    
    credential = db.query(Credential).filter(
        Credential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise NotFoundError("Credential not found")
    
    # Check permissions
    from shared.auth import check_credential_access
    if not check_credential_access(current_user, str(credential.id), db, "write"):
        raise AuthorizationError("Access denied to revoke this credential")
    
    if credential.status == CredentialStatus.REVOKED:
        raise CredentialError("Credential is already revoked")
    
    # Update status
    credential.status = CredentialStatus.REVOKED
    credential.revoked_at = datetime.utcnow()
    credential.revocation_reason = reason
    
    db.commit()
    
    return {"message": "Credential revoked successfully", "credential_id": credential_id}


@app.get("/credentials/{credential_id}/download/{file_type}")
async def download_credential_file(
    credential_id: str,
    file_type: str,  # pdf or png
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db_session)
):
    """Download credential file (PDF or PNG)."""
    
    credential = db.query(Credential).filter(
        Credential.credential_id == credential_id
    ).first()
    
    if not credential:
        raise NotFoundError("Credential not found")
    
    # Check access permissions
    from shared.auth import check_credential_access
    if not check_credential_access(current_user, str(credential.id), db):
        raise AuthorizationError("Access denied to this credential")
    
    # Get file path
    if file_type == "pdf" and credential.pdf_url:
        file_path = credential.pdf_url
    elif file_type == "png" and credential.png_url:
        file_path = credential.png_url
    else:
        raise NotFoundError(f"File type '{file_type}' not available for this credential")
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise NotFoundError("File not found on server")
    
    # Return file
    filename = f"{credential.title}_{credential.credential_id}.{file_type}"
    return FileResponse(
        file_path,
        media_type=f"application/{file_type}" if file_type == "pdf" else "image/png",
        filename=sanitize_filename(filename)
    )


async def generate_credential_files(credential_id: str, template_design: Dict[str, Any]):
    """Background task to generate credential files (PDF and PNG)."""
    # This is a placeholder for the actual file generation logic
    # In a real implementation, you would:
    # 1. Load the template design
    # 2. Merge with credential data
    # 3. Generate PDF and PNG files
    # 4. Update the credential record with file paths
    
    # For now, we'll just create placeholder files
    from sqlalchemy.orm import sessionmaker
    from shared.database import engine
    
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        credential = db.query(Credential).filter(Credential.id == credential_id).first()
        if credential:
            # Create placeholder file paths
            credential.pdf_url = f"/app/uploads/credentials/{credential.credential_id}.pdf"
            credential.png_url = f"/app/uploads/credentials/{credential.credential_id}.png"
            
            # Generate QR code
            qr_code_data = generate_qr_code(credential.verification_url)
            credential.qr_code_url = f"/app/uploads/qr_codes/{credential.credential_id}.png"
            
            # Generate JSON-LD
            json_ld_data = create_json_ld_credential({
                "verification_url": credential.verification_url,
                "issuer_id": str(credential.issuer_id),
                "issuer_name": credential.issuer.first_name + " " + credential.issuer.last_name,
                "recipient_id": str(credential.recipient_id),
                "recipient_name": credential.recipient_name,
                "recipient_email": credential.recipient_email,
                "title": credential.title,
                "description": credential.description,
                "issued_at": credential.issued_at.isoformat() if credential.issued_at else None,
                "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
                "credential_data": credential.credential_data
            })
            credential.json_ld = json_ld_data
            
            db.commit()
    finally:
        db.close()


async def send_credential_notification(credential_id: str):
    """Background task to send credential notification to recipient."""
    # This would integrate with the notification service
    # For now, it's a placeholder
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

