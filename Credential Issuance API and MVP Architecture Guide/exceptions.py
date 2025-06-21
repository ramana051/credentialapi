"""
Custom exceptions for the Digital Credentials Platform.
"""

from fastapi import HTTPException, status


class DCPException(Exception):
    """Base exception for Digital Credentials Platform."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(DCPException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)


class AuthenticationError(DCPException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(DCPException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundError(DCPException):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictError(DCPException):
    """Raised when there's a conflict with existing data."""
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, status.HTTP_409_CONFLICT)


class RateLimitError(DCPException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)


class ExternalServiceError(DCPException):
    """Raised when external service fails."""
    
    def __init__(self, message: str = "External service error", service: str = None):
        self.service = service
        super().__init__(message, status.HTTP_502_BAD_GATEWAY)


class CredentialError(DCPException):
    """Raised when credential operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class VerificationError(DCPException):
    """Raised when credential verification fails."""
    
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class TemplateError(DCPException):
    """Raised when template operations fail."""
    
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


def create_http_exception(exception: DCPException) -> HTTPException:
    """Convert a DCP exception to an HTTP exception."""
    return HTTPException(
        status_code=exception.status_code,
        detail={
            "message": exception.message,
            "type": exception.__class__.__name__
        }
    )

