# BotIQ MCP Server

An extensible, scalable, and minimal Model Context Protocol (MCP) server built with Python and FastAPI. This version features a **Self-Hosted OAuth 2.1 Authenticator** with PKCE (Proof Key for Code Exchange) support, removing dependencies on Azure AD tenant configurations.

## Architecture Overview

This server functions in two distinct security layers:
1. **Layer 1: Self-Hosted OAuth 2.1 Server & Middleware**
   - **Authentication Server**: Provides endpoints for client registration (`/register`), HTML-based user login and code authorization (`/authorize`), and PKCE authorization code exchange (`/token`) to issue HS256-signed JWTs.
   - **Verification Middleware**: Intercepts incoming MCP requests under `/mcp/*`, validating local JWT signatures using a shared `SECRET_KEY`, or falling back to a static bypass token (`MCP_STATIC_TOKEN`) if configured.
2. **Layer 2: Credentials Validation (`validate_user` Tool)**
   - Exposes a standard MCP tool (`validate_user`) to the AI host.
   - Connects to the existing BotIQ Azure Function via an asynchronous HTTP client to validate credentials.
   - Restricts sensitive parameters (passwords) and raw authorization tokens (`authorize_token`) from logging outputs. Truncates tokens in server logging for added security.

---

## Folder Structure

```
botiq-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py                    # MCP & FastAPI entrypoint
│   ├── config.py                    # Configurations loader (SECRET_KEY, etc.)
│   ├── auth_server/
│   │   ├── __init__.py
│   │   ├── register_endpoint.py      # POST /register (registers client)
│   │   ├── authorize_endpoint.py     # GET /authorize (login form), POST /authorize
│   │   ├── token_endpoint.py         # POST /token (exchanges code/refresh)
│   │   ├── pkce_utils.py             # PKCE verification logic
│   │   └── auth_code_store.py        # In-memory auth code store
│   ├── auth/
│   │   ├── __init__.py
│   │   └── token_middleware.py        # Validates self-signed HS256 JWT
│   ├── tools/
│   │   ├── __init__.py
│   │   └── validate_user_tool.py    # MCP tool definition (Layer 2)
│   ├── clients/
│   │   ├── __init__.py
│   │   └── botiq_api_client.py      # Async client for BotIQ Azure Function
│   └── utils/
│       ├── __init__.py
│       └── logger.py                # Security-aware logger
├── .env.example
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Configuration Settings

Configure environment variables in a `.env` file at the root of the project (copy from `.env.example`):

```ini
# Server Transport Config
HOST=0.0.0.0
PORT=8000

# Self-Hosted OAuth Configuration (Layer 1)
# Secret key used to sign and verify JWT access tokens
SECRET_KEY=botiq_secret_key_change_me_in_prod
# JWT signing algorithm (HS256 is default for self-hosted setup)
JWT_ALGORITHM=HS256
# Token expiration time in seconds (e.g. 3600 for 1 hour)
TOKEN_EXPIRY_LIMIT=3600
# Optional static token bypass for local development or testing (empty to disable)
MCP_STATIC_TOKEN=

# BotIQ Function Client Configuration (Layer 2)
# URL of the existing validate_user Azure Function
BOTIQ_VALIDATE_USER_URL=https://your-function-app.azurewebsites.net/api/validate_user
# Expected status success code
STATUS_SUCCESS=200
```

---

## Running the Server Locally

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Set up Virtual Environment
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Running the Server

Set the module path to `src/` so the imports execute correctly:
```bash
# Windows (PowerShell):
$env:PYTHONPATH="src"
# Linux/macOS:
export PYTHONPATH="src"
```

#### Run in Stdio Transport Mode (Default)
Useful for local integrations like Claude Desktop (does not enforce OAuth):
```bash
python src/server.py --transport stdio
```

#### Run in SSE Transport Mode
Starts the FastAPI application with Server-Sent Events transport. This mode enforces OAuth token validation on incoming requests:
```bash
python src/server.py --transport sse
```
The server will start on `http://localhost:8000`. The endpoints will be:
- SSE stream: `http://localhost:8000/mcp/sse`
- JSON-RPC messages (POST): `http://localhost:8000/mcp/messages`
- OAuth Endpoints:
  - Register Client: POST `http://localhost:8000/register`
  - Authorize Code: GET/POST `http://localhost:8000/authorize`
  - Token Exchange: POST `http://localhost:8000/token`

---

## Claude Desktop Configuration

To integrate with Claude Desktop, edit your `claude_desktop_config.json`:

### Stdio Mode (Direct Local Execution)
```json
{
  "mcpServers": {
    "botiq-mcp-server": {
      "command": "python",
      "args": ["d:/BotIq-mcp-server/src/server.py", "--transport", "stdio"],
      "env": {
        "PYTHONPATH": "d:/BotIq-mcp-server/src",
        "BOTIQ_VALIDATE_USER_URL": "https://your-function-app.azurewebsites.net/api/validate_user",
        "STATUS_SUCCESS": "200"
      }
    }
  }
}
```

### SSE Mode (OAuth Validated Remote Connection)
If the server is running on `http://localhost:8000`:
```json
{
  "mcpServers": {
    "botiq-mcp-server": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}
```

---

## Running in Docker

To build and run the Docker image:

```bash
docker build -t botiq-mcp-server .
```

#### Run Stdio Mode
```bash
docker run -i --rm botiq-mcp-server
```

#### Run SSE Mode (with OAuth)
Ensure your `.env` file is loaded:
```bash
docker run -p 8000:8000 --env-file .env botiq-mcp-server --transport sse
```
