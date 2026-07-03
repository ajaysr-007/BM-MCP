import httpx
from config import BOTIQ_VALIDATE_USER_URL

async def call_validate_user(user_id: str, password: str) -> dict:
    """
    Calls the existing Azure Function (validate_user) to validate user credentials.
    """
    headers = {
        "Content-Type": "application/json",
        "request_type": "application/json",
    }
    payload = {"user_id": user_id, "password": password}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(BOTIQ_VALIDATE_USER_URL, json=payload, headers=headers)
        return resp.json()
