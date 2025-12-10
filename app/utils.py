import secrets
import hashlib
from datetime import datetime, timedelta, timezone

def generate_api_key(prefix: str = "sk_live_") -> str:
    """
    Generates a secure, random API key.
    Example: sk_live_7f8a9d...
    """
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"

def hash_api_key(key: str) -> str:
    """
    One-way hashes the API key for storage.
    We use SHA256.
    """
    return hashlib.sha256(key.encode()).hexdigest()

def calculate_expiry(duration: str) -> datetime:
    """
    Parses a duration string (1H, 1D, 1M, 1Y) and returns the future UTC datetime.
    """
    unit = duration[-1].upper()
    
    try:
        value = int(duration[:-1])
    except ValueError:
        raise ValueError("Invalid duration format. Use format like '1D', '30D', '1Y'.")

    now = datetime.now(timezone.utc)
    
    if unit == "H":
        return now + timedelta(hours=value)
    elif unit == "D":
        return now + timedelta(days=value)
    elif unit == "M":
        return now + timedelta(days=value * 30)
    elif unit == "Y":
        return now + timedelta(days=value * 365)
    else:
        raise ValueError(f"Unknown time unit '{unit}'. Supported: H, D, M, Y")