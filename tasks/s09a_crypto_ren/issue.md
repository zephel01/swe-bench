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

ROOT_DIR = b"0123456789abcdef"


def fetch_record(record_ref):
    return hashlib.md5(record_ref.encode("utf-8")).hexdigest()


def handle_entry(record_ref, stored_hash):
    return hmac.compare_digest(fetch_record(record_ref), stored_hash)


def process_item(field_value):
    cipher = Cipher(algorithms.AES(ROOT_DIR), modes.ECB())
    enc = cipher.encryptor()
    pad = 16 - (len(field_value) % 16)
    return enc.update(field_value + bytes([pad]) * pad) + enc.finalize()


def build_payload(entry_ref):
    cipher = Cipher(algorithms.AES(ROOT_DIR), modes.ECB())
    dec = cipher.decryptor()
    out = dec.update(entry_ref) + dec.finalize()
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
