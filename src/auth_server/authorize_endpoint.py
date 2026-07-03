from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from clients.botiq_api_client import call_validate_user
from auth_server.auth_code_store import store_auth_code
from auth_server.register_endpoint import validate_client
import secrets
from utils.logger import logger

router = APIRouter(tags=["OAuth authorization"])

@router.get("/authorize", response_class=HTMLResponse)
async def show_login_form(
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: str,
    code_challenge_method: str = "S256",
):
    if not validate_client(client_id, redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid client_id or redirect_uri")

    logger.info(f"Authorization requested by client_id={client_id} with redirect_uri={redirect_uri}")

    # Clean HTML form using standard input stylings
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BotIQ Login</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f3f4f6;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            .card {{
                background: white;
                padding: 2.5rem;
                border-radius: 12px;
                box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
                width: 100%;
                max-width: 420px;
                box-sizing: border-box;
            }}
            h2 {{
                margin-top: 0;
                margin-bottom: 1.5rem;
                color: #1f2937;
                text-align: center;
                font-weight: 700;
            }}
            .input-group {{
                margin-bottom: 1.25rem;
            }}
            label {{
                display: block;
                margin-bottom: 0.5rem;
                color: #4b5563;
                font-size: 0.875rem;
                font-weight: 500;
            }}
            input {{
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                box-sizing: border-box;
                font-size: 1rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}
            input:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
            }}
            button {{
                width: 100%;
                padding: 0.75rem;
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s;
                margin-top: 0.5rem;
            }}
            button:hover {{
                background-color: #2563eb;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>BotIQ Login</h2>
            <form method="post" action="/authorize">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="code_challenge" value="{code_challenge}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
                <input type="hidden" name="state" value="{state}">
                
                <div class="input-group">
                    <label for="user_id">User ID</label>
                    <input type="text" id="user_id" name="user_id" placeholder="Enter User ID" required>
                </div>
                <div class="input-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter Password" required>
                </div>
                
                <button type="submit">Sign In</button>
            </form>
        </div>
    </body>
    </html>
    """

@router.post("/authorize")
async def handle_login(
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form("S256"),
    state: str = Form(...),
    user_id: str = Form(...),
    password: str = Form(...),
):
    if not validate_client(client_id, redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid client_id or redirect_uri")

    # Check brute-force lockout status
    from auth_server.rate_limiter import is_locked_out, record_failed_attempt, reset_failed_attempts
    if is_locked_out(user_id):
        return HTMLResponse(
            "<h3>This account is temporarily locked out due to too many failed login attempts. Please try again in 15 minutes.</h3>",
            status_code=429
        )

    logger.info(f"Received login request for user_id={user_id} from client_id={client_id}")
    # Validate against existing Azure validate_user endpoint
    result = await call_validate_user(user_id, password)
    if result.get("status_code") != 200:
        remaining = record_failed_attempt(user_id)
        logger.warning(f"Login credentials validation failed for user_id={user_id}. Remaining attempts: {remaining}")
        return HTMLResponse(
            f"<h3>Invalid credentials. Attempts remaining: {remaining}. <a href='javascript:history.back()'>Try again</a></h3>",
            status_code=401
        )

    # Success, reset attempts counter
    reset_failed_attempts(user_id)

    # Issue short-lived authorization code bound to user and client
    auth_code = f"code_{secrets.token_urlsafe(32)}"
    store_auth_code(
        auth_code,
        user_id=user_id,
        client_id=client_id,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        ttl_seconds=200
    )

    logger.info(f"Login successful for user_id={user_id}. Redirecting to {redirect_uri}")
    return RedirectResponse(
        url=f"{redirect_uri}?code={auth_code}&state={state}",
        status_code=303
    )
