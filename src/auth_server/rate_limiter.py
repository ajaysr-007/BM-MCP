import time
from typing import Dict
from utils.logger import logger

# Lockout configurations
MAX_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

# In-memory store: { user_id: { "failed_attempts": int, "lockout_until": float } }
_attempts: Dict[str, dict] = {}

def is_locked_out(user_id: str) -> bool:
    """
    Checks if a user is currently locked out due to brute force protection.
    """
    if user_id not in _attempts:
        return False
        
    data = _attempts[user_id]
    lockout_until = data.get("lockout_until", 0)
    
    if lockout_until > 0:
        if time.time() < lockout_until:
            remaining = int(lockout_until - time.time())
            logger.warning(f"Access blocked for user_id={user_id}. Locked out for another {remaining}s")
            return True
        else:
            # Lockout period expired, reset attempts
            _attempts[user_id] = {"failed_attempts": 0, "lockout_until": 0}
            logger.info(f"Lockout expired for user_id={user_id}. Resetting attempt counter.")
            
    return False

def record_failed_attempt(user_id: str) -> int:
    """
    Records a failed login attempt for a user.
    Locks the user out if failed attempts exceed MAX_ATTEMPTS.
    Returns the remaining attempts before lockout.
    """
    if user_id not in _attempts:
        _attempts[user_id] = {"failed_attempts": 0, "lockout_until": 0}
        
    data = _attempts[user_id]
    data["failed_attempts"] += 1
    
    attempts_remaining = MAX_ATTEMPTS - data["failed_attempts"]
    logger.warning(f"Failed login attempt for user_id={user_id}. Attempts: {data['failed_attempts']}/{MAX_ATTEMPTS}")
    
    if data["failed_attempts"] >= MAX_ATTEMPTS:
        data["lockout_until"] = time.time() + LOCKOUT_DURATION_SECONDS
        logger.error(f"User user_id={user_id} has been locked out for {LOCKOUT_DURATION_SECONDS}s due to too many failed login attempts.")
        return 0
        
    return attempts_remaining

def reset_failed_attempts(user_id: str) -> None:
    """
    Resets the failed attempts counter on a successful login.
    """
    if user_id in _attempts:
        _attempts.pop(user_id)
        logger.info(f"Reset failed attempts counter for user_id={user_id}")
