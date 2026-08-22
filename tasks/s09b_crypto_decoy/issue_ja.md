# セキュリティレビュー課題: 資格情報ボールト

あなたはセキュリティアナリストです。以下の Python モジュールは、ユーザーの
パスワードを保存し、サードパーティ API トークンを保管時に暗号化します。この
コードにセキュリティ上の脆弱性が含まれているかを判定し、含まれている場合は
すべての脆弱性の種類、正確な箇所、および根拠を示してください。異なる問題は
それぞれ別の finding として報告してください。

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
