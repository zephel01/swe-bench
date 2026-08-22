# セキュリティレビュー課題: パスワード保管とトークン暗号化

あなたはセキュリティアナリストです。以下の Python モジュールは、パスワードから
鍵を導出し、API トークンを保管時に暗号化します。このコードに実際のセキュリティ
脆弱性が含まれているかを判定してください。報告するのは実証可能な本物の問題だけに
限り、安全で慣用的なコードや、同等に健全なアルゴリズム間の好みの違いを問題として
挙げないでください。

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

## 出力仕様

分析の後、次の行を正確に 1 行出力してください:

```
--- FINDINGS ---
```

続けて JSON 配列を出力してください。各要素は次の形式のオブジェクトです:

```json
{"type": "...", "location": "...", "evidence": "..."}
```

セキュリティ上の問題が見つからない場合は、空配列 `[]` を出力してください。
