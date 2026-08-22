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
