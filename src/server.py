import argparse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from tools.validate_user_tool import mcp
from auth.token_middleware import validate_local_token
from auth_server.register_endpoint import router as register_router
from auth_server.authorize_endpoint import router as authorize_router
from auth_server.token_endpoint import router as token_router
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import logger
from config import HOST, PORT

app = FastAPI(title="BotIQ MCP Server Wrapper")

# Enable CORS for frontend API calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific origins like ["http://localhost:5500"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the self-hosted OAuth 2.1 authentication server endpoints
app.include_router(register_router)
app.include_router(authorize_router)
app.include_router(token_router)

@app.middleware("http")
async def oauth_middleware(request: Request, call_next):
    # Bypass verification for non-MCP routes, dynamic login/consent endpoints, and health checks
    if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/register", "/authorize", "/token"]:
        return await call_next(request)

    # Protect all mounted MCP routes (e.g. /mcp/sse and /mcp/messages)
    if request.url.path.startswith("/mcp"):
        try:
            payload = await validate_local_token(request)
            request.state.user = payload
        except HTTPException as e:
            logger.warning(f"OAuth token validation failed for {request.url.path}: {e.detail}")
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers,
            )
        except Exception as e:
            logger.exception("Unexpected error during OAuth token validation middleware")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error during authentication check"},
            )

    return await call_next(request)

# Mount FastMCP's SSE app under the /mcp prefix
app.mount("/mcp", mcp.sse_app())

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "botiq-mcp-server"}

def main():
    parser = argparse.ArgumentParser(description="BotIQ MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport to use (default: stdio)",
    )
    args = parser.parse_args()

    if args.transport == "sse":
        logger.info(f"Starting BotIQ MCP Server in SSE mode on {HOST}:{PORT}")
        logger.info(f"SSE Endpoint: http://{HOST}:{PORT}/mcp/sse")
        logger.info(f"Message POST Endpoint: http://{HOST}:{PORT}/mcp/messages")
        uvicorn.run("server:app", host=HOST, port=PORT, reload=False)
    else:
        logger.info("Starting BotIQ MCP Server in Stdio mode")
        mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
