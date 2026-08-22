# セキュリティレビュー課題: セッション状態の取り扱い

あなたはセキュリティアナリストです。以下の Python モジュールは、ユーザーごとの
ダッシュボード状態を Cookie から復元し、ディスク上の既定値とマージします。この
コードにセキュリティ上の脆弱性が含まれているかを判定し、含まれている場合は脆弱性の
種類、正確な箇所、および根拠を示してください。

```python
import base64
import pickle

import yaml
from flask import Flask, request, make_response

app = Flask(__name__)


def load_profile_defaults(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def decode_session(cookie_value):
    raw = base64.b64decode(cookie_value)
    return pickle.loads(raw)


def encode_session(state):
    return base64.b64encode(pickle.dumps(state)).decode("ascii")


@app.route("/dashboard")
def dashboard():
    cookie = request.cookies.get("session_state")
    state = decode_session(cookie) if cookie else {"theme": "light"}
    defaults = load_profile_defaults("/etc/myapp/profile.yaml")
    theme = state.get("theme", defaults.get("theme"))
    resp = make_response(f"theme={theme}")
    resp.set_cookie("session_state", encode_session(state))
    return resp


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
