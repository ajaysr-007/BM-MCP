from fastapi import APIRouter
from pydantic import BaseModel
import secrets
from utils.logger import logger

router = APIRouter(tags=["OAuth client registration"])

# In-memory client repository: { client_id: [redirect_uris] }
_clients = {
    # Default registered client for local development / Claude Desktop fallback
    "claude-desktop": ["http://localhost:8000/callback", "https://localhost:8000/callback"]
}

class RegisterRequest(BaseModel):
    client_name: str
    redirect_uris: list[str]

@router.post("/register")
async def register_client(req: RegisterRequest):
    """
    Registers a new OAuth client application and registers its redirect URIs.
    Since this is a public PKCE client, no client secret is generated.
    """
    client_id = f"client_{secrets.token_hex(8)}"
    _clients[client_id] = req.redirect_uris
    logger.info(f"Registered new client={req.client_name} with client_id={client_id}")
    return {
        "client_id": client_id,
        "client_name": req.client_name,
        "redirect_uris": req.redirect_uris,
    }

def validate_client(client_id: str, redirect_uri: str) -> bool:
    """
    Validates if client_id is registered and redirect_uri is allowed.
    """
    if client_id not in _clients:
        logger.warning(f"Client validation failed: client_id={client_id} not registered")
        return False
        
    allowed_uris = _clients[client_id]
    if redirect_uri not in allowed_uris:
        logger.warning(f"Client validation failed: redirect_uri={redirect_uri} not allowed for client_id={client_id}")
        return False
        
    return True
