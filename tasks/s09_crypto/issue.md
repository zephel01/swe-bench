# Security Review Task: Credential Vault

You are a security analyst. Review the Python module below, which stores user
passwords and encrypts third-party API tokens at rest. Determine whether it
contains security vulnerabilities, and if so, identify every vulnerability
class, its precise location, and the evidence. Report each distinct issue as a
separate finding.

```python
import hashlib
import hmac

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

TOKEN_KEY = b"0123456789abcdef"


def hash_password(password):
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(password, stored_hash):
    return hmac.compare_digest(hash_password(password), stored_hash)


def encrypt_token(token_bytes):
    cipher = Cipher(algorithms.AES(TOKEN_KEY), modes.ECB())
    enc = cipher.encryptor()
    pad = 16 - (len(token_bytes) % 16)
    return enc.update(token_bytes + bytes([pad]) * pad) + enc.finalize()


def decrypt_token(blob):
    cipher = Cipher(algorithms.AES(TOKEN_KEY), modes.ECB())
    dec = cipher.decryptor()
    out = dec.update(blob) + dec.finalize()
    return out[:-out[-1]]
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
