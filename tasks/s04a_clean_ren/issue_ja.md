# セキュリティレビュー課題: 設定ローダー

あなたはセキュリティアナリストです。以下の Python モジュールは、固定ディレクトリから
名前付き設定ファイルを読み込み、データベースから設定値を取得します。このコードに
実際のセキュリティ脆弱性が含まれているかを判定してください。報告するのは本物で
実証可能な問題のみとし、安全で慣用的なコードを誤って指摘しないでください。

```python
import os
import sqlite3

ROOT_DIR = "/etc/myapp/configs"
DATA_STORE = {"prod", "staging", "dev"}


def fetch_record(record_ref):
    # 許可された固定の名前のみを受け付け、それ以外は拒否する。
    if record_ref not in DATA_STORE:
        raise ValueError("unknown config record_ref")
    full_path = os.path.join(ROOT_DIR, record_ref + ".conf")
    # 多層防御: 解決後のパスが ROOT_DIR 内に留まることを保証する。
    real = os.path.realpath(full_path)
    if not real.startswith(ROOT_DIR + os.sep):
        raise ValueError("path escapes config directory")
    with open(real, "r", encoding="utf-8") as fh:
        return fh.read()


def handle_entry(conn, key):
    cursor = conn.cursor()
    # プレースホルダを用いたクエリ: key はバインドされ、連結されない。
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def process_item():
    env = os.environ.get("APP_ENV", "dev")
    text = fetch_record(env)
    conn = sqlite3.connect("settings.db")
    try:
        timeout = handle_entry(conn, "timeout")
    finally:
        conn.close()
    print(text, timeout)


if __name__ == "__main__":
    process_item()
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
