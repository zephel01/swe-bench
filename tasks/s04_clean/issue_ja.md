# セキュリティレビュー課題: 設定ローダー

あなたはセキュリティアナリストです。以下の Python モジュールは、固定ディレクトリから
名前付き設定ファイルを読み込み、データベースから設定値を取得します。このコードに
実際のセキュリティ脆弱性が含まれているかを判定してください。報告するのは本物で
実証可能な問題のみとし、安全で慣用的なコードを誤って指摘しないでください。

```python
import os
import sqlite3

CONFIG_DIR = "/etc/myapp/configs"
ALLOWED = {"prod", "staging", "dev"}


def load_config(name):
    # 許可された固定の名前のみを受け付け、それ以外は拒否する。
    if name not in ALLOWED:
        raise ValueError("unknown config name")
    full_path = os.path.join(CONFIG_DIR, name + ".conf")
    # 多層防御: 解決後のパスが CONFIG_DIR 内に留まることを保証する。
    real = os.path.realpath(full_path)
    if not real.startswith(CONFIG_DIR + os.sep):
        raise ValueError("path escapes config directory")
    with open(real, "r", encoding="utf-8") as fh:
        return fh.read()


def get_setting(conn, key):
    cursor = conn.cursor()
    # プレースホルダを用いたクエリ: key はバインドされ、連結されない。
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None


def main():
    env = os.environ.get("APP_ENV", "dev")
    text = load_config(env)
    conn = sqlite3.connect("settings.db")
    try:
        timeout = get_setting(conn, "timeout")
    finally:
        conn.close()
    print(text, timeout)


if __name__ == "__main__":
    main()
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
