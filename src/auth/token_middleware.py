import jwt
from fastapi import Request, HTTPException
from config import SECRET_KEY, JWT_ALGORITHM, MCP_STATIC_TOKEN
from utils.logger import logger

async def validate_local_token(request: Request) -> dict:
    """
    Validates our self-hosted HS256 JWT authorization token.
    Supports a static token bypass if MCP_STATIC_TOKEN is configured in the environment.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": 'Bearer realm="botiq-mcp"'},
        )

    token = auth_header.split(" ", 1)[1]

    # Check for static bypass token
    if MCP_STATIC_TOKEN and token == MCP_STATIC_TOKEN:
        logger.info("Access authorized via static fallback token (MCP_STATIC_TOKEN bypass)")
        return {"user_id": "static_admin"}

    # Standard self-signed JWT validation
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        if payload.get("type") != "access":
            logger.warning("Access token validation failed: incorrect token type claim")
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired, please refresh")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
