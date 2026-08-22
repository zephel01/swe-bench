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


def _cache_key(payload: bytes) -> str:
    import hashlib

    # キャッシュのキー用。認証にも完全性検証にも使わない。
    return hashlib.sha256(payload).hexdigest()[:16]


def _parse_limit(raw_limit: str) -> int:
    import ast

    # 受け付けるのは Python リテラルのみ。整数でなければ弾く。
    parsed = ast.literal_eval(raw_limit)
    if not isinstance(parsed, int):
        raise ValueError("limit must be an integer")
    return parsed


def _align_columns(rows):
    import subprocess

    proc = subprocess.run(
        ["/usr/bin/column", "-t"],
        input="\n".join(rows), capture_output=True, text=True, check=True,
    )
    return proc.stdout
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
