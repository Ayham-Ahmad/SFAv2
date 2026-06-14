import json
import base64
from cryptography.fernet import Fernet, InvalidToken
from typing import Dict

from api.config import settings

def _get_encryption_key() -> bytes:
    return settings.DB_ENCRYPTION_KEY.encode()

def validate_encryption_key() -> None:
    raw = settings.DB_ENCRYPTION_KEY
    
    if not raw:
        raise ValueError(
            "DB_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    try:
        decoded = base64.urlsafe_b64decode(raw.encode())
    except Exception:
        raise ValueError(
            "DB_ENCRYPTION_KEY is not valid URL-safe base64. "
            "Generate a correct key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    if len(decoded) != 32:
        raise ValueError(
            f"DB_ENCRYPTION_KEY decodes to {len(decoded)} bytes — Fernet requires exactly 32. "
            "Generate a correct key with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    # Round-trip test: encrypt and decrypt a small payload to confirm the key works end-to-end
    try:
        f = Fernet(raw.encode())
        token = f.encrypt(b"sfa-key-check")
        result = f.decrypt(token)
        if result != b"sfa-key-check":
            raise ValueError("Round-trip encrypt/decrypt produced unexpected output.")
    except InvalidToken:
        raise ValueError("DB_ENCRYPTION_KEY failed the round-trip test (InvalidToken). The key may be corrupted.")
    except Exception as e:
        raise ValueError(f"DB_ENCRYPTION_KEY validation failed: {e}")

def encrypt_config(config: Dict) -> str:
    key = _get_encryption_key()
    f = Fernet(key)
    json_data = json.dumps(config)
    return f.encrypt(json_data.encode()).decode()

def decrypt_config(encrypted_data: str) -> Dict:
    if not encrypted_data:
        return {}
    
    key = _get_encryption_key()
    f = Fernet(key)
    decrypted_bytes = f.decrypt(encrypted_data.encode())
    return json.loads(decrypted_bytes.decode())