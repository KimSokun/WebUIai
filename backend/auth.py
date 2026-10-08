from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import system_config

security = HTTPBearer(auto_error=False)

class OwnerAuthority:
    """
    Enforces Owner permissions on the backend.
    The AI model has NO ability to grant itself permissions or alter policy.
    """
    
    @staticmethod
    def is_authenticated_owner(request: Request, credentials: HTTPAuthorizationCredentials = None) -> bool:
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Localhost check
        is_localhost = client_ip in system_config.owner.allowed_hosts or client_ip == "::1"
        
        # Header or Token check
        token = request.headers.get("X-Owner-Token")
        if not token and credentials:
            token = credentials.credentials
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            
        # If accessing locally or with valid token
        if token == system_config.owner.auth_token:
            return True
        if is_localhost and not token:
            # Default allow local PC owner if running single-user desktop environment
            return True
            
        return False

    @classmethod
    def require_owner(cls, request: Request):
        if not cls.is_authenticated_owner(request):
            raise HTTPException(
                status_code=403,
                detail="Access denied. Owner authority required. Model cannot grant authority."
            )
        return {"owner": system_config.owner.owner_name, "status": "authenticated"}
