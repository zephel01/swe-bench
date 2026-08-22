# Security Review Task: Password Storage and Token Encryption

You are a security analyst. Review the Python module below, which derives keys
from passwords and encrypts API tokens at rest. Decide whether it contains a
real security vulnerability. Only report genuine, demonstrable issues — do not
flag safe, idiomatic code, and do not report mere preferences between equally
sound algorithms.

```python
import hmac
import os
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

PBKDF2_ITERATIONS = 600_000
NONCE_LEN = 12


def new_salt():
    return secrets.token_bytes(16)


def derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password)


def store_password(password: str):
    salt = new_salt()
    return salt, derive_key(password.encode("utf-8"), salt)


def verify_password(password: str, salt: bytes, expected: bytes) -> bool:
    candidate = derive_key(password.encode("utf-8"), salt)
    return hmac.compare_digest(candidate, expected)


def encrypt_token(key: bytes, token: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, token, aad)


def decrypt_token(key: bytes, blob: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:NONCE_LEN], blob[NONCE_LEN:], aad)
```

## Output contract

After your analysis, output a line containing exactly:

```
--- FINDINGS ---
```

Then output a JSON array. Each element must be an object of the form:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

If you find no security issues, output an empty array `[]`.
