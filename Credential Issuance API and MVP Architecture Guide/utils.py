"""
Utility functions for the Digital Credentials Platform.
"""

import uuid
import hashlib
import secrets
import qrcode
from io import BytesIO
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import re
from PIL import Image, ImageDraw, ImageFont
import json

from .config import settings


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


def generate_credential_id() -> str:
    """Generate a unique credential ID."""
    # Format: DCP-YYYYMMDD-XXXXXXXX
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"DCP-{date_part}-{random_part}"


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"dcp_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_webhook_secret() -> str:
    """Generate a webhook secret for signature verification."""
    return secrets.token_urlsafe(32)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    import bcrypt
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    import bcrypt
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def generate_qr_code(data: str, size: int = 200) -> str:
    """Generate a QR code and return as base64 encoded image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Resize if needed
    if size != 200:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_str}"


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return re.match(pattern, url) is not None


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe storage."""
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s-.]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename.strip('-.')


def generate_verification_url(credential_id: str, base_url: str = None) -> str:
    """Generate a verification URL for a credential."""
    if base_url is None:
        base_url = "https://verify.digitalcredentials.com"  # Replace with actual domain
    
    return f"{base_url}/verify/{credential_id}"


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """Format datetime for display."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(format_str)


def parse_datetime(dt_str: str) -> datetime:
    """Parse datetime string."""
    try:
        # Try ISO format first
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except ValueError:
        # Try common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse datetime: {dt_str}")


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Convert to lowercase and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug.strip('-')


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def mask_email(email: str) -> str:
    """Mask email address for privacy."""
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def generate_color_palette(base_color: str = "#3B82F6") -> Dict[str, str]:
    """Generate a color palette based on a base color."""
    # This is a simplified version - you might want to use a proper color library
    return {
        "primary": base_color,
        "secondary": "#6B7280",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "info": "#3B82F6"
    }


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate data against a JSON schema."""
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True
    except ImportError:
        # Fallback to basic validation if jsonschema is not available
        return isinstance(data, dict)
    except jsonschema.ValidationError:
        return False


def create_credential_hash(credential_data: Dict[str, Any]) -> str:
    """Create a hash of credential data for blockchain anchoring."""
    # Sort the data to ensure consistent hashing
    sorted_data = json.dumps(credential_data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(sorted_data.encode()).hexdigest()


def generate_json_ld_context() -> Dict[str, Any]:
    """Generate JSON-LD context for credentials."""
    return {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            {
                "dcp": "https://digitalcredentials.com/vocab#",
                "schema": "https://schema.org/",
                "name": "schema:name",
                "description": "schema:description",
                "image": "schema:image",
                "issuer": "dcp:issuer",
                "recipient": "dcp:recipient",
                "credentialSubject": "dcp:credentialSubject",
                "issuanceDate": "dcp:issuanceDate",
                "expirationDate": "dcp:expirationDate"
            }
        ]
    }


def create_json_ld_credential(credential_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a JSON-LD representation of a credential."""
    context = generate_json_ld_context()
    
    json_ld = {
        **context,
        "type": ["VerifiableCredential", "DigitalCredential"],
        "id": credential_data.get("verification_url"),
        "issuer": {
            "id": credential_data.get("issuer_id"),
            "name": credential_data.get("issuer_name"),
            "url": credential_data.get("issuer_url")
        },
        "issuanceDate": credential_data.get("issued_at"),
        "credentialSubject": {
            "id": credential_data.get("recipient_id"),
            "name": credential_data.get("recipient_name"),
            "email": credential_data.get("recipient_email"),
            "achievement": {
                "type": "Achievement",
                "name": credential_data.get("title"),
                "description": credential_data.get("description"),
                "criteria": credential_data.get("criteria", ""),
                "image": credential_data.get("badge_image_url")
            }
        }
    }
    
    # Add expiration date if present
    if credential_data.get("expires_at"):
        json_ld["expirationDate"] = credential_data.get("expires_at")
    
    # Add additional credential data
    if credential_data.get("credential_data"):
        json_ld["credentialSubject"].update(credential_data["credential_data"])
    
    return json_ld


def extract_domain_from_email(email: str) -> Optional[str]:
    """Extract domain from email address."""
    if '@' in email:
        return email.split('@')[1].lower()
    return None


def is_business_email(email: str) -> bool:
    """Check if email appears to be a business email."""
    domain = extract_domain_from_email(email)
    if not domain:
        return False
    
    # Common personal email domains
    personal_domains = {
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'aol.com', 'icloud.com', 'protonmail.com', 'mail.com'
    }
    
    return domain not in personal_domains


def generate_certificate_number() -> str:
    """Generate a unique certificate number."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(3).upper()
    return f"CERT-{timestamp}-{random_suffix}"

