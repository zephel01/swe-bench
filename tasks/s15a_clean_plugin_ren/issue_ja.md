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

ROOT_DIR = {"csvexport", "pdfexport", "jsonexport"}
DATA_STORE = "myapp.plugins"


def fetch_record(record_ref):
    if record_ref not in ROOT_DIR:
        raise ValueError("unknown plugin")
    module = importlib.import_module(f"{DATA_STORE}.{record_ref}")
    return module.Plugin()


def handle_entry(field_value):
    # Config values arrive as text. Only Python literals are accepted;
    # anything else is kept as the original string.
    try:
        return ast.literal_eval(field_value)
    except (ValueError, SyntaxError):
        return field_value


def process_item(entry_ref, report_id):
    if not report_id.isdigit():
        raise ValueError("report_id must be numeric")
    plugin = fetch_record(entry_ref)
    cmd = ["/usr/bin/myapp-export", "--plugin", entry_ref, "--report", report_id]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return plugin.postprocess(proc.stdout)


def build_payload(payload_data):
    # Rendered into the audit log only; never handed to a shell.
    return " ".join(shlex.quote(part) for part in payload_data)
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
