from mcp.server.fastmcp import FastMCP, Context
from clients.botiq_api_client import call_validate_user
from utils.logger import logger
from config import STATUS_SUCCESS

mcp = FastMCP(name="BotIQ MCP Server")

@mcp.tool()
async def validate_user(user_id: str, password: str, ctx: Context) -> dict:
    """
    BotIQ user credentials validate karta hai aur authorize_token deta hai.

    Args:
        user_id: BotIQ user ID.
        password: BotIQ account password.
        ctx: MCP Request Context (automatically injected).
    """
    # Extract OAuth identity if running over HTTP/SSE
    oauth_user = None
    try:
        req_ctx = ctx.request_context
        if req_ctx and req_ctx.request:
            request = req_ctx.request
            oauth_user = getattr(request.state, "user", None)
    except ValueError:
        # Context is not available outside of a request (e.g. CLI/testing)
        pass
    except Exception as e:
        logger.debug(f"Failed to extract request context: {e}")

    if oauth_user:
        logger.info(f"validate_user tool invoked by authenticated user_id: {oauth_user.get('user_id', 'unknown')}")
    else:
        logger.info("validate_user tool invoked (Stdio mode or no active OAuth session context)")

    try:
        logger.info(f"Calling BotIQ validate_user endpoint for user_id={user_id}")
        result = await call_validate_user(user_id, password)

        # Checking function status code against config.STATUS_SUCCESS
        if result.get("status_code") != STATUS_SUCCESS:
            logger.warning(f"validate_user failed for user_id={user_id}: "
                           f"status_code={result.get('status_code')}, error={result.get('error_message')}")
            return {
                "status": "error",
                "message": result.get("error_message") or result.get("status_description") or "Validation failed",
            }

        token = result.get("response_body", {}).get("authorize_token")
        
        # Mask the token for logging to preserve security
        if token:
            masked_token = token[:8] + "..." + token[-8:] if len(token) > 16 else "***"
            logger.info(f"validate_user successful for user_id={user_id}. Token generated: {masked_token}")
        else:
            logger.warning(f"validate_user response succeeded but authorize_token is missing")

        return {"status": "success", "authorize_token": token}

    except Exception:
        logger.exception(f"Exception while validating user_id={user_id}")
        return {"status": "error", "message": "Something went wrong. Try again."}
