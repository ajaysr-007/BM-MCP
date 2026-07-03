import time
from typing import Dict, Optional
from utils.logger import logger

# In-memory store for short-lived authorization codes
# Format: { auth_code: { "user_id": str, "code_challenge": str, "code_challenge_method": str, "expires_at": float } }
_store: Dict[str, dict] = {}

def store_auth_code(
    code: str,
    user_id: str,
    client_id: str,
    code_challenge: str,
    code_challenge_method: str = "S256",
    ttl_seconds: int = 60
) -> None:
    """
    Stores an authorization code with user parameters, client_id, and expiration.
    """
    expires_at = time.time() + ttl_seconds
    _store[code] = {
        "user_id": user_id,
        "client_id": client_id,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": expires_at
    }
    logger.info(f"Stored authorization code (ttl={ttl_seconds}s) for user_id={user_id} bound to client_id={client_id}")

def get_and_delete_auth_code(code: str) -> Optional[dict]:
    """
    Retrieves and immediately invalidates/deletes an authorization code.
    Returns None if the code does not exist or has expired.
    """
    if code not in _store:
        logger.warning("Authorization code not found in store")
        return None
    
    stored = _store.pop(code)
    if time.time() > stored["expires_at"]:
        logger.warning(f"Authorization code has expired for user_id={stored.get('user_id')}")
        return None
        
    return stored
