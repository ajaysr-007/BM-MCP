import os
from pathlib import Path
from dotenv import load_dotenv

# Load env variables from .env file if it exists
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Server Transport Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Self-Hosted OAuth Config
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not configured. The application cannot start in an insecure configuration.")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TOKEN_EXPIRY_LIMIT = int(os.getenv("TOKEN_EXPIRY_LIMIT", "3600"))  # Expiry limit in seconds
MCP_STATIC_TOKEN = os.getenv("MCP_STATIC_TOKEN", "")

# BotIQ Azure Function Config
BOTIQ_VALIDATE_USER_URL = os.getenv("BOTIQ_VALIDATE_USER_URL", "")
STATUS_SUCCESS = int(os.getenv("STATUS_SUCCESS", "200"))
