import json
from cryptography.fernet import Fernet
from typing import Dict

from api.config import settings

def _get_encryption_key() -> bytes:
    return settings.DB_ENCRYPTION_KEY.encode()

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