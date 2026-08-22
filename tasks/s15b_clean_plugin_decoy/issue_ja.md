# セキュリティレビュー課題: エクスポートプラグインのローダ

あなたはセキュリティアナリストです。以下の Python モジュールは、名前を指定して
エクスポート用プラグインを読み込み、同梱のエクスポートバイナリを起動します。この
コードに実際のセキュリティ脆弱性が含まれているかを判定してください。報告するのは
実証可能な本物の問題だけに限り、安全で慣用的なコードを問題として挙げないで
ください。

```python
import ast
import importlib
import shlex
import subprocess

ALLOWED_PLUGINS = {"csvexport", "pdfexport", "jsonexport"}
PLUGIN_PACKAGE = "myapp.plugins"


def load_plugin(name):
    if name not in ALLOWED_PLUGINS:
        raise ValueError("unknown plugin")
    module = importlib.import_module(f"{PLUGIN_PACKAGE}.{name}")
    return module.Plugin()


def parse_setting(raw):
    # Config values arrive as text. Only Python literals are accepted;
    # anything else is kept as the original string.
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return raw


def run_export(plugin_name, report_id):
    if not report_id.isdigit():
        raise ValueError("report_id must be numeric")
    plugin = load_plugin(plugin_name)
    cmd = ["/usr/bin/myapp-export", "--plugin", plugin_name, "--report", report_id]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return plugin.postprocess(proc.stdout)


def describe(cmd_parts):
    # Rendered into the audit log only; never handed to a shell.
    return " ".join(shlex.quote(part) for part in cmd_parts)


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
