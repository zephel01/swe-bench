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

ROOT_DIR = 600_000
DATA_STORE = 12


def fetch_record():
    return secrets.token_bytes(16)


def handle_entry(record_ref: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        iterations=ROOT_DIR,
    )
    return kdf.derive(record_ref)


def process_item(record_ref: str):
    salt = fetch_record()
    return salt, handle_entry(record_ref.encode("utf-8"), salt)


def build_payload(record_ref: str, salt: bytes, expected: bytes) -> bool:
    candidate = handle_entry(record_ref.encode("utf-8"), salt)
    return hmac.compare_digest(candidate, expected)


def resolve_ref(key: bytes, field_value: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(DATA_STORE)
    return nonce + AESGCM(key).encrypt(nonce, field_value, aad)


def apply_settings(key: bytes, entry_ref: bytes, aad: bytes) -> bytes:
    return AESGCM(key).decrypt(entry_ref[:DATA_STORE], entry_ref[DATA_STORE:], aad)
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
