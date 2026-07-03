from fastapi import APIRouter, HTTPException, Form
from auth_server.auth_code_store import get_and_delete_auth_code
from auth_server.pkce_utils import verify_pkce
from config import SECRET_KEY, TOKEN_EXPIRY_LIMIT, JWT_ALGORITHM
import jwt
import datetime
from utils.logger import logger

router = APIRouter(tags=["OAuth token exchange"])

# 7 days expiration for refresh tokens (longer-lived)
REFRESH_TOKEN_EXPIRY_LIMIT = TOKEN_EXPIRY_LIMIT * 24 * 7

def local_generate_access_token(user_id: str) -> str:
    """
    Generates a short-lived local JWT access token.
    Contains "type": "access" claim.
    """
    current_time = datetime.datetime.utcnow()
    payload = {
        "user_id": user_id,
        "type": "access",
        "iat": current_time,
        "exp": current_time + datetime.timedelta(seconds=TOKEN_EXPIRY_LIMIT)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

def local_generate_refresh_token(user_id: str) -> str:
    """
    Generates a longer-lived local JWT refresh token.
    Contains "type": "refresh" claim.
    """
    current_time = datetime.datetime.utcnow()
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "iat": current_time,
        "exp": current_time + datetime.timedelta(seconds=REFRESH_TOKEN_EXPIRY_LIMIT)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

@router.post("/token")
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(None),
    code: str = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
):
    """
    Exchanges an authorization code or refresh token for a local JWT access token.
    Implements PKCE code challenge verification and client-id binding validation.
    """
    if grant_type == "authorization_code":
        if not code or not code_verifier:
            raise HTTPException(status_code=400, detail="code and code_verifier are required")
        if not client_id:
            raise HTTPException(status_code=400, detail="client_id is required")

        stored = get_and_delete_auth_code(code)
        if not stored:
            raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

        # Verify that the client requesting the token matches the one that authorized the code
        if stored.get("client_id") != client_id:
            logger.warning(f"Client mismatch: code is bound to client_id={stored.get('client_id')}, but request has client_id={client_id}")
            raise HTTPException(status_code=400, detail="Client ID mismatch")

        # Perform PKCE match verification
        method = stored.get("code_challenge_method", "S256")
        if not verify_pkce(code_verifier, stored["code_challenge"], method=method):
            raise HTTPException(status_code=400, detail="PKCE verification failed")

        user_id = stored["user_id"]
        # Generate access token and refresh token separately
        access_token = local_generate_access_token(user_id)
        new_refresh_token = local_generate_refresh_token(user_id)
        
        # Mask the token for logging
        masked_access = access_token[:8] + "..." + access_token[-8:] if len(access_token) > 16 else "***"
        logger.info(f"Generated self-signed access_token for user_id={user_id}: {masked_access}")

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": TOKEN_EXPIRY_LIMIT,
            "refresh_token": new_refresh_token,
        }

    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(status_code=400, detail="refresh_token is required")
        try:
            # Decode the refresh token (HS256) to verify signature and type claim
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Prevent using access tokens as refresh tokens
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Invalid token type for refresh")
                
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token claims")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Refresh token expired, please log in again")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid refresh token: {e}")

        logger.info(f"Renewing access_token for user_id={user_id} via refresh_token")
        new_access_token = local_generate_access_token(user_id)
        new_refresh_token = local_generate_refresh_token(user_id)
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": TOKEN_EXPIRY_LIMIT,
            "refresh_token": new_refresh_token,
        }

    raise HTTPException(status_code=400, detail="Unsupported grant_type")
