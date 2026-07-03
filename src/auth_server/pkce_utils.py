import hashlib
import base64
from utils.logger import logger

def verify_pkce(code_verifier: str, code_challenge: str, method: str = "S256") -> bool:
    """
    Verifies the PKCE code_verifier against the code_challenge.
    Supports both 'plain' and 'S256' methods.
    """
    if not code_verifier or not code_challenge:
        logger.warning("PKCE verification failed: missing verifier or challenge")
        return False

    if method == "plain":
        return code_verifier == code_challenge

    elif method == "S256":
        try:
            # Hash verifier using SHA-256
            sha256_hash = hashlib.sha256(code_verifier.encode("ascii")).digest()
            # Base64url encode without padding
            encoded_bytes = base64.urlsafe_b64encode(sha256_hash)
            encoded_str = encoded_bytes.decode("ascii").rstrip("=")
            return encoded_str == code_challenge
        except Exception as e:
            logger.error(f"Error during PKCE S256 hashing: {e}")
            return False

    logger.warning(f"PKCE verification failed: unsupported method={method}")
    return False
